import ast
import logging
from collections import defaultdict

import requests

from os import getenv
from datetime import datetime, time, timedelta
from operator import itemgetter
from lxml import etree

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger()

from .indirect_percent_expenses import STRING_FIELDNAMES
from ..ozon_api import (
    MIN_FIX_EXPENSES_FBS,
    MAX_FIX_EXPENSES_FBS,
    MIN_FIX_EXPENSES_FBO,
    MAX_FIX_EXPENSES_FBO,
)

from ..helpers import (
    split_list,
    split_keywords,
    split_keywords_on_slash,
    remove_latin_characters,
    remove_duplicates_from_list,
    mean,
)


class Product(models.Model):
    _name = "ozon.products"
    _description = "Лоты"

    # GPT
    description = fields.Text(string="Описание товара")
    tracked_search_queries = fields.One2many(
        "ozon.tracked_search_queries", "link_ozon_products", string="Поисковые запросы"
    )

    categories = fields.Many2one("ozon.categories", string="Название категории")
    id_on_platform = fields.Char(string="Product ID", readonly=True)
    sku = fields.Char(string="SKU", readonly=True)
    fbo_sku = fields.Char(string="FBO SKU", readonly=True)
    fbs_sku = fields.Char(string="FBS SKU", readonly=True)
    article = fields.Char(string="Артикул", readonly=True)

    supplementary_categories = fields.Many2many(
        "ozon.supplementary_categories",
        string="Вспомогательные категории",
        readonly=True,
    )
    products = fields.Many2one("retail.products", string="Товар")
    price = fields.Float(string="Актуальная цена", readonly=True)
    expected_price = fields.Float(
        string="Ожидаемая цена", readonly=True, compute="_compute_expected_price"
    )
    price_delta = fields.Float(
        string="Разница между актуальной и ожидаемой ценой",
        readonly=True,
        compute="_compute_price_delta",
    )
    old_price = fields.Float(string="Цена до учёта скидок", readonly=True)
    ext_comp_min_price = fields.Float(
        string="Минимальная цена товара у конкурентов на другой площадке", readonly=True
    )
    ozon_comp_min_price = fields.Float(
        string="Минимальная цена товара у конкурентов на Ozon", readonly=True
    )
    self_marketplaces_min_price = fields.Float(
        string="Минимальная цена вашего товара на других площадках", readonly=True
    )
    price_index = fields.Selection(
        [
            ("WITHOUT_INDEX", "Без индекса"),
            ("PROFIT", "Выгодный"),
            ("AVG_PROFIT", "Умеренный"),
            ("NON_PROFIT", "Невыгодный"),
        ],
        string="Ценовой индекс",
        readonly=True,
    )

    imgs_urls = fields.Char(string="Ссылки на изображения")
    imgs_html = fields.Html(compute="_compute_imgs")
    seller = fields.Many2one("retail.seller", string="Продавец")
    insurance = fields.Float(string="Страховой коэффициент, %")
    search_queries = fields.One2many(
        "ozon.search_queries", "product_id", string="Ключевые слова"
    )
    trading_scheme = fields.Selection(
        [("FBS", "FBS"), ("FBO", "FBO"), ("FBS, FBO", "FBS, FBO"), ("undefined", " ")],
        string="Схема торговли",
    )

    delivery_location = fields.Selection(
        [
            ("PC", "ППЗ/PC"),
            ("PP", "ПВЗ/PP"),
            ("SC", "СЦ/SC"),
            ("TSC", "ТСЦ/TSC"),
            ("", ""),
        ],
        string="Пункт приема товара",
        help=(
            "ППЦ - Пункт приема заказов (Pickup Center), "
            "ПВЗ - Пункт выдачи заказов (Pickup Point), "
            "СЦ - Сервисный центр (Service Center)"
        ),
    )

    competitors_with_price_ids = fields.One2many(
        "ozon.price_history_competitors",
        "product_id",
        string="Актуальные цены конкурентов",
    )
    not_enough_competitors = fields.Boolean()
    commentary_not_enough_competitors = fields.Char()

    price_our_history_ids = fields.One2many(
        "ozon.price_history", "product_id", string="История цен"
    )
    stock_ids = fields.One2many("ozon.stock", "product", string="История остатков")
    stock_history_count = fields.Integer(compute="_compute_stock_history_count")
    stocks_fbs = fields.Integer(string="FBS остатки", readonly=True)
    stocks_fbo = fields.Integer(string="FBO остатки", readonly=True)
    is_selling = fields.Boolean(
        string="В продаже", compute="_get_is_selling", store=True, readonly=True
    )
    is_alive = fields.Boolean(string="Живой товар", readonly=True)
    is_participating_in_actions = fields.Boolean(
        string="Участвует в акциях", readonly=True
    )

    fix_expenses = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты",
        copy=True,
        readonly=True,
    )
    # FBO fix expenses
    fbo_fix_expenses_min = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты минимальные (FBO)",
        readonly=True,
        domain=[("name", "in", MIN_FIX_EXPENSES_FBO)],
    )
    total_fbo_fix_expenses_min = fields.Float(
        string="Итого", compute="_compute_total_fbo_fix_expenses_min", store=True
    )
    fbo_fix_expenses_max = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты максимальные (FBO)",
        readonly=True,
        domain=[("name", "in", MAX_FIX_EXPENSES_FBO)],
    )
    total_fbo_fix_expenses_max = fields.Float(
        string="Итого", compute="_compute_total_fbo_fix_expenses_max", store=True
    )
    # FBS fix expenses
    fbs_fix_expenses_min = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты минимальные (FBS)",
        readonly=True,
        domain=[("name", "in", MIN_FIX_EXPENSES_FBS)],
    )
    total_fbs_fix_expenses_min = fields.Float(
        string="Итого", compute="_compute_total_fbs_fix_expenses_min", store=True
    )
    fbs_fix_expenses_max = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты максимальные (FBS)",
        readonly=True,
        domain=[("name", "in", MAX_FIX_EXPENSES_FBS)],
    )
    total_fbs_fix_expenses_max = fields.Float(
        string="Итого", compute="_compute_total_fbs_fix_expenses_max", store=True
    )

    percent_expenses = fields.One2many(
        "ozon.cost",
        "product_id",
        string="Процент от продаж",
        copy=True,
        readonly=True,
    )

    fbo_percent_expenses = fields.One2many(
        "ozon.cost",
        "product_id",
        string="Процент от продаж (FBO)",
        readonly=True,
        domain=[
            (
                "name",
                "in",
                [
                    "Процент комиссии за продажу (FBO)",
                    "Общий коэффициент косвенных затрат",
                ],
            )
        ],
    )
    total_fbo_percent_expenses = fields.Float(
        string="Итого", compute="_compute_total_fbo_percent_expenses", store=True
    )

    fbs_percent_expenses = fields.One2many(
        "ozon.cost",
        "product_id",
        string="Процент от продаж (FBS)",
        readonly=True,
        domain=[
            (
                "name",
                "in",
                [
                    "Процент комиссии за продажу (FBS)",
                    "Общий коэффициент косвенных затрат",
                ],
            )
        ],
    )
    total_fbs_percent_expenses = fields.Float(
        string="Итого", compute="_compute_total_fbs_percent_expenses", store=True
    )
    all_expenses_ids = fields.One2many(
        "ozon.all_expenses", "product_id", string="Все затраты", readonly=True
    )
    total_all_expenses_ids = fields.Float(
        string="Итого общих затрат, исходя из актуальной цены",
        compute="_compute_total_all_expenses_ids",
    )
    total_expected_price_all_expenses_ids = fields.Float(
        string="Итого общих затрат, исходя из ожидаемой цены",
        compute="_compute_total_expected_price_all_expenses_ids",
    )
    total_all_expenses_ids_except_tax_roe_roi = fields.Float(
        string="Итого общих затрат без налогов, ROE, ROI, исходя из актуальной цены",
        compute="_compute_total_all_expenses_ids_except_tax_roe_roi",
    )
    product_fee = fields.Many2one("ozon.product_fee", string="Комиссии товара Ozon")
    posting_ids = fields.Many2many("ozon.posting", string="Отправления Ozon")
    postings_count = fields.Integer(compute="_compute_count_postings")
    fbo_supply_order_product_ids = fields.One2many(
        "ozon.fbo_supply_order_product", "product_id", string="Поставки"
    )
    supply_orders_count = fields.Integer(compute="_compute_supply_orders_count")
    sales = fields.One2many(
        "ozon.sale",
        "product",
        string="Продажи",
        copy=True,
        readonly=True,
    )
    sales_per_day_last_30_days = fields.Float(
        string="Среднее кол-во продаж в день за последние 30 дней",
    )
    sales_per_day_last_30_days_group = fields.Char(
        string="Группа коэффициента продаваемости",
    )
    investment_expenses_id = fields.Many2one(
        "ozon.investment_expenses", string="Investment"
    )
    profitability_norm = fields.Many2one(
        "ozon.profitability_norm", string="Ожидаемая доходность"
    )
    coef_profitability = fields.Float(
        string="Отклонение от прибыли",
    )
    coef_profitability_group = fields.Char(
        string="Группа отклонения от прибыли",
    )
    profit = fields.Float(
        string="Прибыль от актуальной цены", compute="_compute_profit"
    )
    profit_ideal = fields.Float(
        string="Идеальная прибыль", compute="_compute_profit_ideal"
    )
    profit_delta = fields.Float(
        string="Разница между прибылью и идеальной прибылью",
        compute="_compute_profit_delta",
    )
    pricing_strategy_id = fields.Many2one(
        "ozon.pricing_strategy", string="Стратегия назначения цен"
    )
    pricing_strategy_ids = fields.Many2many(
        "ozon.pricing_strategy", string="Стратегии назначения цен"
    )
    product_calculator_ids = fields.One2many(
        "ozon.product_calculator",
        "product_id",
        string="Рассчитываемые параметры",
    )
    get_sales_count = fields.Integer(compute="compute_count_sales")
    price_history_count = fields.Integer(compute="compute_count_price_history")
    action_candidate_ids = fields.One2many(
        "ozon.action_candidate", "product_id", string="Кандидат в акциях"
    )
    # indicators
    ozon_products_indicator_ids = fields.One2many(
        "ozon.products.indicator", inverse_name="ozon_product_id"
    )
    ozon_products_indicators_summary_ids = fields.One2many(
        "ozon.products.indicator.summary", inverse_name="ozon_product_id"
    )

    retail_product_total_cost_price = fields.Float(
        compute="_compute_total_cost_price", store=True
    )
    # ABC analysis
    revenue_share_temp = fields.Float()
    revenue_cumulative_share_temp = fields.Float()
    abc_group = fields.Char(size=3)

    market_share = fields.Float(string='Доля рынка')

    def _compute_expected_price(self):
        # TODO: откуда берем РРЦ?
        # ожид.цена=фикс.затраты/(1-процент_затрат-ожид.ROS-проц.налог-ожид.ROI)
        for rec in self:
            all_fix_expenses = rec.all_expenses_ids.filtered(lambda r: r.kind == "fix")
            sum_fix_expenses = sum(all_fix_expenses.mapped("value"))
            all_per_expenses = rec.all_expenses_ids.filtered(
                lambda r: r.kind == "percent"
            )
            total_percent = sum(all_per_expenses.mapped("percent"))
            # print(f"{rec.expected_price} = {sum_fix_expenses}/(1 - {total_percent})")
            rec.expected_price = sum_fix_expenses / (1 - total_percent)
            # print(rec.expected_price)

    def _compute_price_delta(self):
        for rec in self:
            rec.price_delta = rec.price - rec.expected_price

    @api.depends("products.total_cost_price")
    def _compute_total_cost_price(self):
        for record in self:
            total_cost_prise = record.products.total_cost_price
            record.retail_product_total_cost_price = total_cost_prise
            record._check_cost_price(record)

    @api.depends("sales")
    def compute_count_sales(self):
        for record in self:
            record.get_sales_count = len(record.sales)

    def get_sales(self):
        self.ensure_one()

        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90)

        return {
            "type": "ir.actions.act_window",
            "name": "История продаж",
            "view_mode": "tree,graph",
            "res_model": "ozon.sale",
            "domain": [
                ("product", "=", self.id),
                ("date", ">=", three_months_ago.strftime("%Y-%m-%d %H:%M:%S")),
            ],
            "context": {
                "create": False,
                "views": [(False, "tree"), (False, "form"), (False, "graph")],
                "graph_mode": "line",
                "measure": "revenue",
                "interval": "day",
            },
        }

    @api.depends("price_our_history_ids")
    def compute_count_price_history(self):
        for record in self:
            record.price_history_count = len(record.price_our_history_ids)

    def history_price(self):
        self.ensure_one()

        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90)

        return {
            "type": "ir.actions.act_window",
            "name": "История цен",
            "view_mode": "tree,graph",
            "res_model": "ozon.price_history",
            "domain": [
                ("product_id", "=", self.id),
                ("timestamp", ">=", three_months_ago.strftime("%Y-%m-%d %H:%M:%S")),
            ],
            "context": {
                "create": False,
                "views": [(False, "tree"), (False, "form"), (False, "graph")],
                "graph_mode": "line",
                "measure": "profit",
                "interval": "day",
            },
        }

    def _compute_profit(self):
        for rec in self:
            rec.profit = rec.price - rec.total_all_expenses_ids_except_tax_roe_roi

    @api.depends("price", "profitability_norm.value")
    def _compute_profit_ideal(self):
        for record in self:
            if record.profitability_norm:
                record.profit_ideal = record.price * record.profitability_norm.value
            else:
                record.profit_ideal = record.price * 0.2

    @api.depends("profit", "profit_ideal")
    def _compute_profit_delta(self):
        for record in self:
            record.profit_delta = record.profit - record.profit_ideal

    @api.depends("fbo_fix_expenses_min.price")
    def _compute_total_fbo_fix_expenses_min(self):
        for record in self:
            record.total_fbo_fix_expenses_min = sum(
                record.fbo_fix_expenses_min.mapped("price")
            )

    @api.depends("fbo_fix_expenses_max.price")
    def _compute_total_fbo_fix_expenses_max(self):
        for record in self:
            record.total_fbo_fix_expenses_max = sum(
                record.fbo_fix_expenses_max.mapped("price")
            )

    @api.depends("fbs_fix_expenses_min.price")
    def _compute_total_fbs_fix_expenses_min(self):
        for record in self:
            record.total_fbs_fix_expenses_min = sum(
                record.fbs_fix_expenses_min.mapped("price")
            )

    @api.depends("fbs_fix_expenses_max.price")
    def _compute_total_fbs_fix_expenses_max(self):
        for record in self:
            record.total_fbs_fix_expenses_max = sum(
                record.fbs_fix_expenses_max.mapped("price")
            )

    @api.depends("fbo_percent_expenses.price")
    def _compute_total_fbo_percent_expenses(self):
        for record in self:
            record.total_fbo_percent_expenses = sum(
                record.fbo_percent_expenses.mapped("price")
            )

    @api.depends("fbs_percent_expenses.price")
    def _compute_total_fbs_percent_expenses(self):
        for record in self:
            record.total_fbs_percent_expenses = sum(
                record.fbs_percent_expenses.mapped("price")
            )

    def _compute_total_all_expenses_ids(self):
        for rec in self:
            rec.total_all_expenses_ids = sum(rec.all_expenses_ids.mapped("value"))

    def _compute_total_expected_price_all_expenses_ids(self):
        for rec in self:
            rec.total_expected_price_all_expenses_ids = sum(
                rec.all_expenses_ids.mapped("expected_value")
            )

    def _compute_total_all_expenses_ids_except_tax_roe_roi(self):
        for rec in self:
            all_expenses_except_tax_roe_roi = rec.all_expenses_ids.filtered(
                lambda r: r.category not in ["Рентабельность", "Налоги", "Investment"]
            )
            total_expenses = sum(all_expenses_except_tax_roe_roi.mapped("value"))
            rec.total_all_expenses_ids_except_tax_roe_roi = total_expenses

    @api.depends("price_our_history_ids.price")
    def _compute_price_history_values(self):
        for product in self:
            product.price_history_values = [
                (record.timestamp, record.price)
                for record in product.price_our_history_ids
            ]

    @api.depends("sales")
    def _compute_sales_per_day_last_30_days(self):
        for product in self:
            date_from = datetime.combine(datetime.now(), time.min) - timedelta(days=30)
            date_to = datetime.combine(datetime.now(), time.max) - timedelta(days=1)
            # взять все продажи за посл 30 дней
            sales = self.env["ozon.sale"].search(
                [
                    ("product", "=", product.id),
                    ("date", ">", date_from),
                    ("date", "<", date_to),
                ]
            )
            # суммировать qty всех продаж
            total_qty = sum(sales.mapped("qty"))
            # делить эту сумму на 30
            product.sales_per_day_last_30_days = total_qty / 30

    def _compute_sales_per_day_last_30_days_group(self):
        coefs = self.read(fields=["sales_per_day_last_30_days"])
        coefs = sorted(coefs, key=itemgetter("sales_per_day_last_30_days"))
        if coefs:
            g1, g2, g3, g4, g5 = list(split_list(coefs, 5))
            for i, g in enumerate([g1, g2, g3, g4, g5]):
                g_min = round(g[0]["sales_per_day_last_30_days"], 2)
                g_max = round(g[-1]["sales_per_day_last_30_days"], 2)
                for item in g:
                    prod = self.env["ozon.products"].search([("id", "=", item["id"])])
                    prod.sales_per_day_last_30_days_group = (
                        f"Группа {i+1}: от {g_min} до {g_max}"
                    )

    @api.onchange("profit_delta", "profit_ideal")
    @api.depends("profit_delta", "profit_ideal")
    def _compute_coef_profitability(self):
        for product in self:
            if product.profit_ideal:
                product.coef_profitability = round(
                    product.profit_delta / product.profit_ideal, 2
                )
            else:
                product.coef_profitability = 0

    def _compute_coef_profitability_group(self):
        coefs = self.read(fields=["coef_profitability"])
        coefs = sorted(coefs, key=itemgetter("coef_profitability"))
        if coefs:
            g1, g2, g3, g4, g5 = list(split_list(coefs, 5))
            for i, g in enumerate([g1, g2, g3, g4, g5]):
                g_min = round(g[0]["coef_profitability"], 2)
                g_max = round(g[-1]["coef_profitability"], 2)
                for item in g:
                    prod = self.env["ozon.products"].search([("id", "=", item["id"])])
                    prod.coef_profitability_group = (
                        f"Группа {i+1}: от {g_min*100}% до {g_max*100}%"
                    )

    @api.model
    def create(self, values):
        existing_record = self.search(
            [("id_on_platform", "=", values.get("id_on_platform"))]
        )
        if existing_record:
            return existing_record

        records = super(Product, self).create(values)
        for record in records:
            self._check_cost_price(record)
            self._check_competitors_with_price_ids_qty(record)

        return records

    def create_update_fix_exp_cost_price(self, total_cost_price):
        self.ensure_one()
        fix_exp_id = None
        fix_expenses = self.fix_expenses.read(["name"])
        for i in fix_expenses:
            if i["name"] == "Себестоимость товара":
                fix_exp_id = i["id"]
                break
        # if fix_exp_rec_cost_price := self.env["ozon.fix_expenses"].search(
        #     [("product_id", "=", self.id), ("name", "=", "Себестоимость товара")],
        #     limit=1,
        #     order="create_date desc",
        # ):
        #     fix_exp_rec_cost_price.price = total_cost_price
        if fix_exp_id:
            self.percent_expenses = [(1, fix_exp_id, {"price": total_cost_price})]
        else:
            fix_exp_id = (
                self.env["ozon.fix_expenses"]
                .create(
                    {
                        "name": "Себестоимость товара",
                        "price": total_cost_price,
                        "discription": "Общая себестоимость товара",
                        "product_id": self.id,
                    }
                )
                .id
            )
        return fix_exp_id

    def write(self, values, **kwargs):
        if isinstance(values, dict) and values.get("fix_expenses"):
            total_cost_price = self.products.total_cost_price
            fix_exp_rec_cost_price_id = self.create_update_fix_exp_cost_price(
                total_cost_price
            )
            values["fix_expenses"] = [fix_exp_rec_cost_price_id] + values[
                "fix_expenses"
            ]

            per_exp_recs = kwargs.get("percent_expenses")
            names = [rec.name for rec in per_exp_recs]
            for per_exp in self.percent_expenses:
                if per_exp.name not in names:
                    values["percent_expenses"].append(per_exp.id)

        res = super(Product, self).write(values)
        if values.get("not_enough_competitors"):
            self._not_enough_competitors_write(self)
        if values.get("competitors_with_price_ids"):
            self._check_competitors_with_price_ids_qty(self)

        return res

    def _update_indicator_summary(self, record):
        self_indicators = record.ozon_products_indicator_ids
        if self_indicators:
            indicator_types = defaultdict()
            for indicator in self_indicators:
                indicator_types[indicator.type] = indicator
            summary_types = defaultdict()
            for summary in record.ozon_products_indicators_summary_ids:
                summary_types[summary.type] = summary

            # cost price
            indicator_cost_price = indicator_types.get("cost_not_calculated")
            if indicator_cost_price:
                days = (datetime.now() - indicator_cost_price.create_date).days
                summary = summary_types.get("cost_not_calculated")
                if summary:
                    summary.name = (
                        f"Себестоимость не подсчитана дней: {days}. "
                        f"Точность расчета цены может быть снижена. Добавьте себестоимость продукта."
                    )
                else:
                    self.env["ozon.products.indicator.summary"].create(
                        {
                            "name": f"Себестоимость не подсчитана дней: {days}. "
                            f"Точность расчета цены может быть снижена. Добавьте себестоимость продукта.",
                            "type": "cost_not_calculated",
                            "ozon_product_id": record.id,
                        }
                    )

            else:
                summary = summary_types.get("cost_not_calculated")
                if summary:
                    record.ozon_products_indicators_summary_ids = [(2, summary.id, 0)]

            # less 3 competitors
            indicator_no_competitor_r = indicator_types.get("no_competitor_robot")
            indicator_no_competitor_m = indicator_types.get("no_competitor_manager")
            if indicator_no_competitor_r and not indicator_no_competitor_m:
                days = (datetime.now() - indicator_no_competitor_r.create_date).days
                summary = summary_types.get("no_competitor_robot")
                if summary:
                    summary.name = (
                        f"Продукт имеет менее 3х конкурентов в течение дней: {days}. "
                        f"Цена не может быть рассчитана. Добавьте товары конкурентов."
                    )
                else:
                    self.env["ozon.products.indicator.summary"].create(
                        {
                            "name": f"Продукт имеет менее 3х конкурентов в течение дней: {days}. "
                            f"Цена не может быть рассчитана. Добавьте товары конкурентов.",
                            "type": "no_competitor_robot",
                            "ozon_product_id": record.id,
                        }
                    )

            elif indicator_no_competitor_r and indicator_no_competitor_m:
                manager = indicator_no_competitor_m.user_id
                expiration_date = indicator_no_competitor_m.expiration_date.strftime(
                    "%d.%m.%Y"
                )
                create_date = indicator_no_competitor_m.create_date.strftime("%d.%m.%Y")
                summary_m = summary_types.get("no_competitor_manager")
                if summary_m:
                    summary_m.name = (
                        f"{manager.name} {create_date} подтвердил, что у продукта менее 3х "
                        f"товаров- конкурентов. Цена может быть рассчитана без их учета, "
                        f"что снизит точность прогнозирования правильной ценовой стратегии. "
                        f"Этот индикатор будет действовать до {expiration_date}"
                    )
                else:
                    self.env["ozon.products.indicator.summary"].create(
                        {
                            "name": f"{manager.name} {create_date} подтвердил, что у продукта менее 3х "
                            f"товаров- конкурентов. Цена может быть рассчитана без их учета, "
                            f"что снизит точность прогнозирования правильной ценовой стратегии. "
                            f"Этот индикатор будет действовать до {expiration_date}",
                            "type": "no_competitor_manager",
                            "ozon_product_id": record.id,
                        }
                    )

                # delete robot's summary
                summary_r = summary_types.get("no_competitor_robot")
                if summary_r:
                    record.ozon_products_indicators_summary_ids = [(2, summary_r.id, 0)]
            elif not indicator_no_competitor_r:
                summary_r = summary_types.get("no_competitor_robot")
                summary_m = summary_types.get("no_competitor_manager")
                for summary in (summary_r, summary_m):
                    if summary:
                        record.ozon_products_indicators_summary_ids = [
                            (2, summary.id, 0)
                        ]

            # остатки
            in_stock_indicator = indicator_types.get("in_stock")
            out_of_stock_indicator = indicator_types.get("out_of_stock")
            in_stock_summary = summary_types.get("in_stock")
            out_of_stock_summary = summary_types.get("out_of_stock")
            if in_stock_indicator:
                days = (datetime.now() - in_stock_indicator.create_date).days
                if out_of_stock_summary:
                    record.ozon_products_indicators_summary_ids = [
                        (2, out_of_stock_summary.id, 0)
                    ]
                if in_stock_summary:
                    in_stock_summary.name = f"Товар в продаже дней: {days}."
                else:
                    self.env["ozon.products.indicator.summary"].create(
                        {
                            "name": f"Товар в продаже дней: {days}.",
                            "type": "in_stock",
                            "ozon_product_id": record.id,
                        }
                    )
            elif out_of_stock_indicator:
                days = (datetime.now() - out_of_stock_indicator.create_date).days
                if in_stock_summary:
                    record.ozon_products_indicators_summary_ids = [
                        (2, in_stock_summary.id, 0)
                    ]
                if out_of_stock_summary:
                    out_of_stock_summary.name = f"Товар отсутствует дней: {days}."
                else:
                    self.env["ozon.products.indicator.summary"].create(
                        {
                            "name": f"Товар отсутствует дней: {days}.",
                            "type": "out_of_stock",
                            "ozon_product_id": record.id,
                        }
                    )

    def _check_investment_expenses(self, record):
        if not record.investment_expenses_id:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_investment_expenses":
                    found = 1
                    break
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "no_investment_expenses",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )
        else:
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_investment_expenses":
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
        # обновить выводы по индикаторам
        self._update_indicator_summary(record)

    def _check_profitability_norm(self, record):
        if not record.profitability_norm:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_profitability_norm":
                    found = 1
                    break
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "no_profitability_norm",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )
        else:
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_profitability_norm":
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
        # обновить выводы по индикаторам
        self._update_indicator_summary(record)

    def _check_cost_price(self, record):
        cost_price = 0
        if record.fix_expenses:
            cost_price_record = [
                x for x in record.fix_expenses if x.name == "Себестоимость товара"
            ]
            if len(cost_price_record) == 1:
                cost_price = cost_price_record[0].price
        if cost_price == 0:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "cost_not_calculated":
                    found = 1
                    break
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "cost_not_calculated",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )
        else:
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "cost_not_calculated":
                    indicator.end_date = datetime.now().date()
                    indicator.active = False

        # обновить выводы по индикаторам
        self._update_indicator_summary(record)

    def _check_competitors_with_price_ids_qty(self, record):
        if len(record.competitors_with_price_ids) >= 3:
            for indicator in record.ozon_products_indicator_ids:
                if (
                    indicator.type == "no_competitor_manager"
                    or indicator.type == "no_competitor_robot"
                ):
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
        elif len(record.competitors_with_price_ids) < 3:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_competitor_robot":
                    found = 1
                    break
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "no_competitor_robot",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )

        # обновить выводы по индикаторам
        self._update_indicator_summary(record)

    def _update_in_out_stock_indicators(self, record):
        if record.is_selling:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "out_of_stock":
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
                if indicator.type == "in_stock":
                    found = 1
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "in_stock",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )
        else:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "in_stock":
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
                if indicator.type == "out_of_stock":
                    found = 1
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "out_of_stock",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )
        # обновить выводы по индикаторам
        self._update_indicator_summary(record)

    def _automated_daily_action_by_cron(self):
        types_for_report = [
            "no_competitor_robot",
            "cost_not_calculated",
            "out_of_stock",
        ]
        products = self.env["ozon.products"].search([])
        lots_with_indicators = defaultdict(list)
        for record in products:
            # проверяет не устарел ли индикатор и архивирует если да
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_competitor_manager":
                    if indicator.expiration_date <= datetime.now().date():
                        indicator.end_date = datetime.now().date()
                        indicator.active = False
            # проверяет есть ли 3 конкурента и если нет вешает индикатор
            self._check_competitors_with_price_ids_qty(record)

            summary_types = defaultdict()
            for summary in record.ozon_products_indicators_summary_ids:
                summary_types[summary.type] = summary

            for type_ in summary_types:
                if type_ in types_for_report:
                    lots_with_indicators[record.categories.category_manager.id].append(
                        record.id
                    )
                    break

        self._create_manager_indicator_report(lots_with_indicators)

    def _create_manager_indicator_report(self, lots_with_indicators):
        reports = self.env["ozon.report"].search([("type", "=", "indicators")])
        for report in reports:
            report.active = False
        for manager_id, lots_ids in lots_with_indicators.items():
            if manager_id:
                report = self.env["ozon.report"].create(
                    {
                        "type": "indicators",
                        "res_users_id": manager_id,
                        "ozon_products_ids": lots_ids,
                        "lots_quantity": len(lots_ids),
                    }
                )

    def _not_enough_competitors_write(self, record):
        if (
            record.not_enough_competitors
            and not record.commentary_not_enough_competitors
        ):
            raise UserError("Напишите комментарий")
        for indicator in record.ozon_products_indicator_ids:
            if indicator.type == "no_competitor_manager":
                indicator.end_date = datetime.now().date()
                indicator.active = False

        user_id = self.env.uid
        user_name = self.env["res.users"].browse(user_id).name
        exp_date = datetime.now() + timedelta(days=30)
        self.env["ozon.products.indicator"].create(
            {
                "ozon_product_id": record.id,
                "source": "manager",
                "type": "no_competitor_manager",
                "expiration_date": exp_date.date(),
                "user_id": user_id if user_id else False,
            }
        )

        # обновить выводы по индикаторам
        self._update_indicator_summary(record)

    @api.depends("stocks_fbs", "stocks_fbo")
    def _get_is_selling(self):
        for record in self:
            if record.stocks_fbs > 0 or record.stocks_fbo > 0:
                record.is_selling = True
            else:
                record.is_selling = False
            self._update_in_out_stock_indicators(record)

    def _compute_is_alive(self):
        for record in self:
            cost_price = self.env["retail.cost_price"].search(
                [("product_id", "=", record.products.id)]
            )
            if cost_price and (
                record.is_selling or record.sales_per_day_last_30_days > 0
            ):
                record.is_alive = True
            else:
                record.is_alive = False

    def update_coefs_and_groups(self):
        all_products = self.search([])
        for i, prod in enumerate(all_products):
            # coefs
            prod._compute_coef_profitability()
            prod._compute_sales_per_day_last_30_days()
            # product calculator ids
            prod._compute_product_calculator_ids()
            # is_alive
            prod._compute_is_alive()
            print(
                f"{i} - Product {prod.id_on_platform} calculator_ids, coef_profitability, sales_per_day_last_30_days and is_alive were updated"
            )
        # groups
        alive_products = self.search([("is_alive", "=", True)])
        not_alive_products = all_products - alive_products
        for i, rec in enumerate(not_alive_products):
            rec.coef_profitability_group = ""
            rec.sales_per_day_last_30_days_group = ""
            print(f"{i} - Not alive product {rec.id_on_platform} was updated")
        alive_products._compute_coef_profitability_group()
        alive_products._compute_sales_per_day_last_30_days_group()

    def populate_search_queries(self, keywords_string):
        # разделить полученную из csv string keywords на слова
        keywords = split_keywords(keywords_string)

        data = []
        for word in keywords:
            # если такое слово уже ассоциировано с продуктом, то его не добавляем
            if self.env["ozon.search_queries"].search(
                [
                    ("words", "=", word),
                    ("product_id", "=", self.id),
                ]
            ):
                continue

            record = {"words": word, "product_id": self.id}
            data.append((0, 0, record))
            print(f"Word {word} added.")

        if data:
            # добавить слова к продукту
            self.search_queries = data

    def populate_supplementary_categories(
        self, full_categories_string: str, full_categories_id: int
    ):
        cats_list = split_keywords_on_slash(full_categories_string)
        cats_list = remove_duplicates_from_list(cats_list)

        sup_cat_ids = []
        for cat in cats_list:
            if (
                sup_cat_id := self.env["ozon.supplementary_categories"]
                .search([("sc_id", "=", full_categories_id), ("name", "=", cat)])
                .id
            ):
                pass
            else:
                sup_cat_id = (
                    self.env["ozon.supplementary_categories"]
                    .create({"sc_id": full_categories_id, "name": cat})
                    .id
                )

            sup_cat_ids.append(sup_cat_id)

        self.supplementary_categories = [(6, 0, sup_cat_ids)]

    def update_percent_expenses(self):
        latest_indirect_expenses = self.env["ozon.indirect_percent_expenses"].search(
            [],
            limit=1,
            order="create_date desc",
        )
        coef_total = latest_indirect_expenses.coef_total / 100
        coef_total_percentage_string = f"{coef_total:.2%}"

        all_products = self.env["ozon.products"].search([])
        for i, product in enumerate(all_products):
            percent_expenses_records = []
            per_exp_record = self.env["ozon.cost"].create(
                {
                    "name": "Общий коэффициент косвенных затрат",
                    "price": round(product.price * coef_total, 2),
                    "discription": coef_total_percentage_string,
                    "product_id": product.id,
                }
            )
            percent_expenses_records.append(per_exp_record.id)
            sale_percent_com_recs = product.percent_expenses.search(
                [
                    ("product_id", "=", product.id),
                    (
                        "name",
                        "in",
                        [
                            "Процент комиссии за продажу (FBO)",
                            "Процент комиссии за продажу (FBS)",
                        ],
                    ),
                ],
            )
            if sale_percent_com_recs:
                percent_expenses_records.extend(sale_percent_com_recs.ids)

            product.percent_expenses = [(6, 0, percent_expenses_records)]

            print(
                f"{i} - Product {product.id_on_platform} percent expenses were updated."
            )

    def update_all_expenses(self):
        latest_indirect_expenses = self.env["ozon.indirect_percent_expenses"].search(
            [], limit=1, order="id desc"
        )
        all_products = self.env["ozon.products"].search([])
        self.env["ozon.all_expenses"].create_update_all_product_expenses(
            all_products, latest_indirect_expenses
        )

    def update_current_product_all_expenses(self):
        self.ensure_one()
        latest_indirect_expenses = self.env["ozon.indirect_percent_expenses"].search(
            [], limit=1, order="id desc"
        )
        self.env["ozon.all_expenses"].create_update_all_product_expenses(
            self, latest_indirect_expenses
        )

    def get_view(self, view_id=None, view_type="form", **options):
        res = super(Product, self).get_view(view_id=view_id, view_type=view_type)
        if view_type == "form":
            # view = self.env["ir.ui.view"].search([("id", "=", res["id"])], limit=1)
            doc = etree.XML(res["arch"])
            af = "autofocus"
            params = self.env.context.get("params")
            if params:
                prod_id = params.get("id")
                if prod_id:
                    prod = self.browse(prod_id)
                    if prod.trading_scheme == "FBS":
                        doc.xpath('//page[@id="page_fbs_fix"]')[0].set(af, af)
                        doc.xpath('//page[@id="page_fbs_percent"]')[0].set(af, af)

                    elif prod.trading_scheme == "FBO":
                        doc.xpath('//page[@id="page_fbo_fix"]')[0].set(af, af)
                        doc.xpath('//page[@id="page_fbo_percent"]')[0].set(af, af)

            res["arch"] = etree.tostring(doc, encoding="unicode")

        return res

    def create_mass_pricing(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Добавить в очередь на изменение цен",
            "view_mode": "form",
            "res_model": "ozon.mass_pricing",
            "target": "new",
            "context": {
                "default_product": self.id,
                "default_price": self.price,
                "default_new_price": self.price,
            },
        }

    def _compute_imgs(self):
        for rec in self:
            rec.imgs_html = False
            if rec.imgs_urls:
                render_html = []
                imgs_urls_list = ast.literal_eval(rec.imgs_urls)
                for img in imgs_urls_list:
                    render_html.append(f"<img src='{img}' width='400'/>")

                rec.imgs_html = "\n".join(render_html)

    @api.onchange("pricing_strategy_id")
    def onchange_pricing_stragegy_id(self):
        if self.pricing_strategy_id.strategy_id == "lower_3_percent_min_competitor":
            # if product has at least one competitor
            if min_comp_price := self.env.context.get("min_competitors_price"):
                multiple = self.pricing_strategy_id.value
                self.price = round(min_comp_price * multiple, 2)

    def calculator(self):
        self.ensure_one()
        calculator_view = self.env["ir.ui.view"].search(
            [("model", "=", "ozon.products"), ("name", "=", "Калькулятор")]
        )
        comp_prices = self.price_history_ids.mapped("price")
        min_competitors_price = min(comp_prices) if comp_prices else None
        return {
            "type": "ir.actions.act_window",
            "name": "Калькулятор",
            "view_mode": "form",
            "view_id": calculator_view.id,
            "res_model": "ozon.products",
            "res_id": self.id,
            "target": "new",
            "context": {
                "default_products": self.id,
                "default_price": self.price,
                "default_profit": self.profit,
                "default_profitability_norm": self.profitability_norm,
                "default_coef_profitability": self.coef_profitability,
                "default_total_fbs_fix_expenses_max": self.total_fbs_fix_expenses_max,
                "default_total_fbo_fix_expenses_max": self.total_fbo_fix_expenses_max,
                "default_total_fbs_percent_expenses": self.total_fbs_percent_expenses,
                "default_total_fbo_percent_expenses": self.total_fbo_percent_expenses,
                "min_competitors_price": min_competitors_price,
            },
        }

    def reset_calculator(self):
        self.profitability_norm = False
        self.pricing_strategy_id = False
        return self.calculator()

    def _compute_product_calculator_ids(self):
        for rec in self:
            if pc_recs := rec.product_calculator_ids:
                for pc_rec in pc_recs:
                    if pc_rec.name == "Ожидаемая цена по всем стратегиям":
                        pc_rec.value = rec.price
            else:
                self.env["ozon.product_calculator"].create(
                    [
                        {
                            "name": "Ожидаемая цена по всем стратегиям",
                            "product_id": rec.id,
                            "value": rec.price,
                        }
                    ]
                )

    def calculate_pricing_stragegy_ids(self):
        prod_calc_recs = self.env["ozon.product_calculator"].browse(
            self.product_calculator_ids.ids
        )
        if not self.pricing_strategy_ids:
            for prod_calc_rec in prod_calc_recs:
                prod_calc_rec.new_value = 0
            return

        if sum(self.pricing_strategy_ids.mapped("weight")) != 1:
            raise UserError("Суммарный вес стратегий должен составлять 1.")
        prices = []
        errors = False
        for price_strategy in self.pricing_strategy_ids:
            strategy_value = price_strategy.value
            strategy_id = price_strategy.strategy_id

            # общие условия для всех стратегий
            if ind_sum := self.ozon_products_indicators_summary_ids.filtered(
                lambda r: r.type == "cost_not_calculated"
            ):
                errors = True
                price_strategy.message = ind_sum.name

            # TODO: переделать, когда появятся соотв. индикаторы
            if not self.profitability_norm:
                errors = True
                price_strategy.message = (
                    "Невозможно рассчитать цену. Задайте ожидаемую доходность"
                )

            if not self.investment_expenses_id:
                errors = True
                price_strategy.message = (
                    "Невозможно рассчитать цену. Задайте Investment"
                )

            if strategy_id == "lower_min_competitor":
                if ind_sum := self.ozon_products_indicators_summary_ids.filtered(
                    lambda r: r.type.startswith("no_competitor")
                ):
                    price_strategy.message = ind_sum.name
                    errors = True
                else:
                    comp_prices = self.competitors_with_price_ids.mapped("price")
                    min_comp_price = min(comp_prices)
                    new_price = round(min_comp_price * (1 - strategy_value), 2)

            if strategy_id == "expected_price":
                new_price = self.expected_price

            if errors:
                self.pricing_strategy_ids.value = None
                self.pricing_strategy_ids.expected_price = None
                return

            price_strategy.expected_price = new_price
            prices.append(round(new_price * price_strategy.weight))

        for prod_calc_rec in prod_calc_recs:
            if prod_calc_rec.name == "Ожидаемая цена по всем стратегиям":
                prod_calc_rec.new_value = mean(prices)

    def calculate(self):
        # TODO: удалить после тестов
        # latest_indirect_expenses = self.env["ozon.indirect_percent_expenses"].search(
        #     [],
        #     limit=1,
        #     order="create_date desc",
        # )
        # latest_indirect_expenses.coef_total = 15
        self._compute_product_calculator_ids()
        self.update_current_product_all_expenses()
        self.calculate_pricing_stragegy_ids()
        return super(Product, self).write({})

    @api.depends("posting_ids")
    def _compute_count_postings(self):
        for record in self:
            record.postings_count = len(record.posting_ids)

    def get_postings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "История продаж",
            "view_mode": "tree",
            "res_model": "ozon.posting",
            "domain": [
                ("product_ids", "in", [self.id]),
            ],
            "context": {"create": False},
        }

    def _compute_supply_orders_count(self):
        for record in self:
            record.supply_orders_count = len(record.fbo_supply_order_product_ids)

    def get_supply_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Поставки",
            "view_mode": "tree,form",
            "res_model": "ozon.fbo_supply_order_product",
            "domain": [
                ("product_id", "=", [self.id]),
            ],
            "context": {"create": False},
        }

    def _compute_stock_history_count(self):
        for rec in self:
            rec.stock_history_count = len(rec.stock_ids)

    def get_stocks(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "История остатков",
            "view_mode": "tree,form",
            # "res_id": self.id,
            "res_model": "ozon.stock",
            "domain": [
                ("product", "=", [self.id]),
            ],
            "context": {"create": False},
        }


class ProductNameGetExtension(models.Model):
    _inherit = "ozon.products"

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, f"{record.article}, {record.products.name}"))
        return result


class ProductQuikSearchExtension(models.Model):
    _inherit = "ozon.products"

    def _name_search(
        self, name="", args=None, operator="ilike", limit=10, name_get_uid=None
    ):
        args = list(args or [])
        if name:
            args += ["|", ("article", operator, name), ("products", operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)


class ProductKanbanExtension(models.Model):
    _inherit = "ozon.products"

    img_html = fields.Html(compute="_compute_img")

    def _compute_img(self):
        for rec in self:
            rec.img_html = False
            if rec.imgs_urls:
                render_html = []
                imgs_urls_list = ast.literal_eval(rec.imgs_urls)
                for img in imgs_urls_list:
                    render_html.append(f"<img src='{img}' width='150'/>")
                    break

                rec.img_html = "\n".join(render_html)


class ProductGraphExtension(models.Model):
    _inherit = "ozon.products"

    def action_draw_graphs(self):
        self.draw_sale()
        self.draw_sale_per_weeks()
        self.draw_price_history()
        self.draw_stock()
        self.draw_analysis_data()

    ### История цен (модель: ozon.price_history)
    img_data_price_history = fields.Text(string="Данные графика")
    img_url_price_history = fields.Char(string="Ссылка на объект")
    img_html_price_history = fields.Html(compute="_compute_img_price_history")

    def _compute_img_price_history(self):
        for rec in self:
            rec.img_html_price_history = False
            if not rec.img_url_price_history:
                continue

            rec.img_html_price_history = (
                f"<img src='{rec.img_url_price_history}' width='600'/>"
            )

    def draw_price_history(self):
        model_price_history = self.env["ozon.price_history"]
        year = self._get_year()

        for rec in self:
            payload = {
                "model": "price_history",
                "product_id": rec.id,
            }

            records = model_price_history.search(
                [
                    ("product", "=", rec.id),
                    ("timestamp", ">=", f"{year}-01-01"),
                    ("timestamp", "<=", f"{year}-12-31"),
                ]
            )
            graph_data = {"dates": [], "num": []}
            for record in records:
                graph_data["dates"].append(record.timestamp.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.price)
            payload["current"] = graph_data

            # rec.img_data_price_history = graph_data

            self._send_request(payload)

    ### История продаж по неделям (модель: ozon.sale)
    img_data_sale_two_weeks = fields.Text(string="Данные графика")
    img_url_sale_two_weeks = fields.Char(string="Ссылка на объект")
    img_html_sale_two_weeks = fields.Html(compute="_compute_img_sale_two_weeks")

    def _compute_img_sale_two_weeks(self):
        for rec in self:
            rec.img_html_sale_two_weeks = False
            if not rec.img_url_sale_two_weeks:
                continue

            rec.img_html_sale_two_weeks = (
                f"<img src='{rec.img_url_sale_two_weeks}' width='600'/>"
            )

    img_data_sale_six_weeks = fields.Text(string="Данные графика")
    img_url_sale_six_weeks = fields.Char(string="Ссылка на объект")
    img_html_sale_six_weeks = fields.Html(compute="_compute_img_sale_six_weeks")

    def _compute_img_sale_six_weeks(self):
        for rec in self:
            rec.img_html_sale_six_weeks = False
            if not rec.img_url_sale_six_weeks:
                continue

            rec.img_html_sale_six_weeks = (
                f"<img src='{rec.img_url_sale_six_weeks}' width='600'/>"
            )

    img_data_sale_twelve_weeks = fields.Text(string="Данные графика")
    img_url_sale_twelve_weeks = fields.Char(string="Ссылка на объект")
    img_html_sale_twelve_weeks = fields.Html(compute="_compute_img_sale_twelve_weeks")

    def _compute_img_sale_twelve_weeks(self):
        for rec in self:
            rec.img_html_sale_twelve_weeks = False
            if not rec.img_url_sale_twelve_weeks:
                continue

            rec.img_html_sale_twelve_weeks = (
                f"<img src='{rec.img_url_sale_twelve_weeks}' width='600'/>"
            )

    def draw_sale_per_weeks(self):
        model_sale = self.env["ozon.sale"]

        current_date = datetime.now()
        two_week_ago = current_date - timedelta(weeks=2)
        six_week_ago = current_date - timedelta(weeks=6)
        twelve_week_ago = current_date - timedelta(weeks=12)

        for rec in self:
            payload = {
                "model": "sale_by_week",
                "product_id": rec.id,
            }

            records = model_sale.search(
                [
                    ("product", "=", rec.id),
                    ("date", ">=", two_week_ago.strftime("%Y-%m-%d")),
                    ("date", "<=", current_date.strftime("%Y-%m-%d")),
                ]
            )
            graph_data = {"dates": [], "num": []}
            for record in records:
                graph_data["dates"].append(record.date.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.qty)
            payload["two_weeks"] = graph_data

            # rec.img_data_sale_two_weeks = graph_data

            records = model_sale.search(
                [
                    ("product", "=", rec.id),
                    ("date", ">=", six_week_ago.strftime("%Y-%m-%d")),
                    ("date", "<=", current_date.strftime("%Y-%m-%d")),
                ]
            )
            graph_data = {"dates": [], "num": []}
            for record in records:
                graph_data["dates"].append(record.date.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.qty)
            payload["six_week"] = graph_data

            # rec.img_data_sale_six_weeks = graph_data

            records = model_sale.search(
                [
                    ("product", "=", rec.id),
                    ("date", ">=", twelve_week_ago.strftime("%Y-%m-%d")),
                    ("date", "<=", current_date.strftime("%Y-%m-%d")),
                ]
            )
            graph_data = {"dates": [], "num": []}
            for record in records:
                graph_data["dates"].append(record.date.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.qty)
            payload["twelve_week"] = graph_data

            # rec.img_data_sale_twelve_weeks = graph_data

            self._send_request(payload)

    ### История продаж (модель: ozon.sale)
    img_data_sale_this_year = fields.Text(string="Данные графика")
    img_url_sale_this_year = fields.Char(string="Ссылка на объект")
    img_html_sale_this_year = fields.Html(compute="_compute_img_sale_this_year")

    def _compute_img_sale_this_year(self):
        for rec in self:
            rec.img_html_sale_this_year = False
            if not rec.img_url_sale_this_year:
                continue

            rec.img_html_sale_this_year = (
                f"<img src='{rec.img_url_sale_this_year}' width='600'/>"
            )

    img_data_sale_last_year = fields.Text(string="Ссылки на объект")
    img_url_sale_last_year = fields.Char(string="Ссылки на объект")
    img_html_sale_last_year = fields.Html(compute="_compute_img_sale_last_year")

    def _compute_img_sale_last_year(self):
        for rec in self:
            rec.img_html_sale_last_year = False
            if not rec.img_url_sale_last_year:
                continue

            rec.img_html_sale_last_year = (
                f"<img src='{rec.img_url_sale_last_year}' width='600'/>"
            )

    def draw_sale(self):
        model_sale = self.env["ozon.sale"]
        year = datetime.now().year
        last_year = year - 1

        for rec in self:
            payload = {
                "model": "sale",
                "product_id": rec.id,
            }

            records = model_sale.search(
                [
                    ("product", "=", rec.id),
                    ("date", ">=", f"{year}-01-01"),
                    ("date", "<=", f"{year}-12-31"),
                ]
            )

            graph_data = {"dates": [], "values": []}
            for record in records:
                graph_data["dates"].append(record.date.strftime("%Y-%m-%d"))
                graph_data["values"].append(record.qty)
            payload["current"] = graph_data

            if rec.categories.img_data_sale_this_year:
                payload[
                    "average_graph_this_year"
                ] = rec.categories.img_data_sale_this_year

            records = model_sale.search(
                [
                    ("product", "=", rec.id),
                    ("date", ">=", f"{last_year}-01-01"),
                    ("date", "<=", f"{last_year}-12-31"),
                ]
            )

            graph_data = {"dates": [], "values": []}
            for record in records:
                graph_data["dates"].append(record.date.strftime("%Y-%m-%d"))
                graph_data["values"].append(record.qty)
            payload["last"] = graph_data

            if rec.categories.img_data_sale_last_year:
                payload[
                    "average_graph_last_year"
                ] = rec.categories.img_data_sale_last_year

            self._send_request(payload)

    ### История остатков (модель: ozon.stock)
    img_data_stock = fields.Text(string="Данные графика")
    img_url_stock = fields.Char(string="Ссылка на объект")
    img_html_stock = fields.Html(compute="_compute_img_stock")

    def _compute_img_stock(self):
        for rec in self:
            rec.img_html_stock = False
            if not rec.img_url_stock:
                continue

            rec.img_html_stock = f"<img src='{rec.img_url_stock}' width='600'/>"

    def draw_stock(self):
        model_stock = self.env["ozon.stock"]
        year = datetime.now().year

        for rec in self:
            payload = {
                "model": "stock",
                "product_id": rec.id,
            }

            records = model_stock.search(
                [
                    ("product", "=", rec.id),
                    ("timestamp", ">=", f"{year}-01-01"),
                    ("timestamp", "<=", f"{year}-12-31"),
                ]
            )

            graph_data = {"dates": [], "num": []}
            for record in records:
                graph_data["dates"].append(record.timestamp.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.stocks_fbs)
            payload["current"] = graph_data

            self._send_request(payload)

    ### График интереса (модель: ozon.analysis_data)
    img_data_analysis_data = fields.Text(string="Данные графика")
    img_url_analysis_data = fields.Char(string="Ссылка на объект")
    img_html_analysis_data = fields.Html(compute="_compute_img_analysis_data")

    def _compute_img_analysis_data(self):
        for rec in self:
            rec.img_html_analysis_data = False
            if not rec.img_url_analysis_data:
                continue

            rec.img_html_analysis_data = (
                f"<img src='{rec.img_url_analysis_data}' width='600'/>"
            )

    def draw_analysis_data(self):
        model_analysis_data = self.env["ozon.analysis_data"]
        year = self._get_year()

        for rec in self:
            records = model_analysis_data.search(
                [
                    ("product", "=", rec.id),
                    ("timestamp_from", ">=", f"{year}-01-01"),
                    ("timestamp_to", "<=", f"{year}-12-31"),
                ]
            )

            payload = {
                "model": "analysis_data",
                "product_id": rec.id,
                "hits_view": None,
                "hits_tocart": None,
                "average_data": None,
            }

            graph_data = {"dates": [], "num": []}
            for record in records:
                start_date = record.timestamp_from
                end_date = record.timestamp_to
                average_date = start_date + (end_date - start_date) / 2

                graph_data["dates"].append(average_date.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.hits_view)
            payload["hits_view"] = graph_data

            graph_data = {"dates": [], "num": []}
            for record in records:
                start_date = record.timestamp_from
                end_date = record.timestamp_to
                average_date = start_date + (end_date - start_date) / 2

                graph_data["dates"].append(average_date.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.hits_tocart)
            payload["hits_tocart"] = graph_data

            if rec.categories.img_data_analysis_data_this_year:
                payload[
                    "average_data"
                ] = rec.categories.img_data_analysis_data_this_year

            self._send_request(payload)

    def _get_year(self):
        return datetime.now().year

    def _get_records(self, model, record, year, timestamp_field):
        return model.search(
            [
                ("product", "=", record.id),
                (timestamp_field, ">=", f"{year}-01-01"),
                (timestamp_field, "<=", f"{year}-12-31"),
            ]
        )

    def _send_request(self, payload):
        endpoint = "http://django:8000/api/v1/draw_graph"
        api_token = getenv("API_TOKEN_DJANGO")
        headers = {"Authorization": f"Token {api_token}"}
        response = requests.post(endpoint, json=payload, headers=headers)

        if response.status_code != 200:
            raise ValueError(f"{response.status_code}--{response.text}")

    def action_open_lot_full_screen(self):
        return {
            "name": "Лот",
            "type": "ir.actions.act_window",
            "res_model": "ozon.products",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }


class ProductCalculator(models.Model):
    _name = "ozon.product_calculator"
    _description = "Калькулятор лота"

    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    name = fields.Char(string="Параметр", readonly=True)
    value = fields.Float(string="Текущее значение", readonly=True)
    new_value = fields.Float(string="Новое значение")
