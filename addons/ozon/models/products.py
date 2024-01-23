import ast
import requests

from os import getenv
from datetime import datetime, time, timedelta
from operator import itemgetter
from lxml import etree

from odoo import models, fields, api

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
    id_on_platform = fields.Char(string="ID на площадке", unique=True)
    article = fields.Char(string="Артикул", unique=True)

    supplementary_categories = fields.One2many(
        "ozon.supplementary_categories",
        "product_id",
        string="Вспомогательные категории",
        copy=True,
        readonly=True,
    )
    products = fields.Many2one("retail.products", string="Товар")
    price = fields.Float(string="Актуальная цена", readonly=True)
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
    imgs_url_price_history_this_year = fields.Char(
        string='Ссылка на объект "История цен конкурентов"'
    )
    imgs_url_this_year = fields.Char(
        string="Ссылка на объект аналитический данных за этот год"
    )
    imgs_url_last_year = fields.Char(
        string="Ссылки на объект аналитических данных за прошлый год"
    )
    imgs_html_price_history_this_year = fields.Html(
        compute="_compute_imgs_price_history_this_year"
    )
    imgs_html_analysis_data_this_year = fields.Html(
        compute="_compute_imgs_analysis_data_this_year"
    )
    imgs_html_analysis_data_last_year = fields.Html(
        compute="_compute_imgs_analysis_data_last_year"
    )

    imgs_urls = fields.Char(string="Ссылки на изображения")
    imgs_html = fields.Html(compute="_compute_imgs")
    seller = fields.Many2one("retail.seller", string="Продавец")
    index_localization = fields.Many2one(
        "ozon.localization_index", string="Индекс локализации"
    )
    insurance = fields.Float(string="Страховой коэффициент, %")
    search_queries = fields.One2many(
        "ozon.search_queries", "product_id", string="Ключевые слова"
    )
    trading_scheme = fields.Selection(
        [("FBS", "FBS"), ("FBO", "FBO"), ("FBS, FBO", "FBS, FBO"), ("", "")],
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

    price_our_history_ids = fields.One2many(
        "ozon.price_history", "product_id", string="История цен"
    )
    stock_ids = fields.One2many("ozon.stock", "product", string="История остатков")
    stock_history_count = fields.Integer(compute="_compute_stock_history_count")
    stocks_fbs = fields.Integer(string="Остатки FBS", readonly=True)
    stocks_fbo = fields.Integer(string="Остатки FBO", readonly=True)
    is_selling = fields.Boolean(
        string="В продаже", compute="_get_is_selling", store=True, readonly=True
    )
    is_alive = fields.Boolean(
        string="Живой товар",
        readonly=True,
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
    profitability_norm = fields.Many2one(
        "ozon.profitability_norm", string="Норма прибыльности"
    )
    coef_profitability = fields.Float(
        string="Отклонение от прибыли",
    )
    coef_profitability_group = fields.Char(
        string="Группа отклонения от прибыли",
    )
    profit = fields.Float(
        string="Прибыль от актуальной цены", compute="_compute_profit", store=True
    )
    profit_ideal = fields.Float(
        string="Идеальная прибыль", compute="_compute_profit_ideal", store=True
    )
    profit_delta = fields.Float(
        string="Разница между прибылью и идеальной прибылью",
        compute="_compute_profit_delta",
        store=True,
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
        readonly=True,
    )
    get_sales_count = fields.Integer(compute="compute_count_sales")
    price_history_count = fields.Integer(compute="compute_count_price_history")
    action_candidate_ids = fields.One2many(
        "ozon.action_candidate", "product_id", string="Кандидат в акциях"
    )

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

    @api.depends(
        "price",
        "total_fbs_fix_expenses_max",
        "total_fbo_fix_expenses_max",
        "total_fbs_percent_expenses",
        "total_fbo_percent_expenses",
    )
    def _compute_profit(self):
        for record in self:
            if record.trading_scheme == "FBS":
                record.profit = (
                    record.price
                    - record.total_fbs_fix_expenses_max
                    - record.total_fbs_percent_expenses
                )
            elif record.trading_scheme == "FBO":
                record.profit = (
                    record.price
                    - record.total_fbo_fix_expenses_max
                    - record.total_fbo_percent_expenses
                )
            # TODO: удалить после того, как все товары будут либо FBS, либо FBO
            else:
                record.profit = (
                    record.price
                    - record.total_fbs_fix_expenses_max
                    - record.total_fbs_percent_expenses
                )

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
            product.coef_profitability = round(
                product.profit_delta / product.profit_ideal, 2
            )

    def _compute_coef_profitability_group(self):
        coefs = self.read(fields=["coef_profitability"])
        coefs = sorted(coefs, key=itemgetter("coef_profitability"))
        g1, g2, g3, g4, g5 = list(split_list(coefs, 5))
        for i, g in enumerate([g1, g2, g3, g4, g5]):
            g_min = round(g[0]["coef_profitability"], 2)
            g_max = round(g[-1]["coef_profitability"], 2)
            for item in g:
                prod = self.env["ozon.products"].search([("id", "=", item["id"])])
                prod.coef_profitability_group = (
                    f"Группа {i+1}: от {g_min*100}% до {g_max*100}%"
                )

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.products.name))
        return result

    @api.model
    def create(self, values):
        existing_record = self.search(
            [("id_on_platform", "=", values.get("id_on_platform"))]
        )
        if existing_record:
            return existing_record

        return super(Product, self).create(values)

    def get_total_cost_price(self):
        ret_product = self.env["retail.products"].search(
            [("id", "=", self.products.id)]
        )
        return ret_product.total_cost_price

    def create_update_fix_exp_cost_price(self, total_cost_price):
        self.ensure_one()
        if fix_exp_rec_cost_price := self.env["ozon.fix_expenses"].search(
            [("product_id", "=", self.id), ("name", "=", "Себестоимость товара")],
            limit=1,
            order="create_date desc",
        ):
            fix_exp_rec_cost_price.price = total_cost_price
        else:
            fix_exp_rec_cost_price = self.env["ozon.fix_expenses"].create(
                {
                    "name": "Себестоимость товара",
                    "price": total_cost_price,
                    "discription": "Общая себестоимость товара",
                    "product_id": self.id,
                }
            )
        return fix_exp_rec_cost_price

    def write(self, values, current_product=None):
        if isinstance(values, dict) and values.get("fix_expenses"):
            total_cost_price = current_product.get_total_cost_price()
            fix_exp_rec_cost_price = current_product.create_update_fix_exp_cost_price(
                total_cost_price
            )
            values["fix_expenses"] = [fix_exp_rec_cost_price.id] + values[
                "fix_expenses"
            ]

        return super(Product, self).write(values)

    @api.depends("stocks_fbs", "stocks_fbo")
    def _get_is_selling(self):
        for record in self:
            if record.stocks_fbs > 0 or record.stocks_fbo > 0:
                record.is_selling = True
            else:
                record.is_selling = False

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
            # product calculator ids
            prod._compute_product_calculator_ids()
            # coefs
            prod._compute_coef_profitability()
            prod._compute_sales_per_day_last_30_days()
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

    def populate_supplementary_categories(self, full_categories_string: str):
        cats_list = split_keywords_on_slash(full_categories_string)
        cats_list = remove_duplicates_from_list(cats_list)

        sup_cat_data = [{"name": cat, "product_id": self.id} for cat in cats_list]
        sup_cat_recs = self.env["ozon.supplementary_categories"].create(sup_cat_data)
        self.supplementary_categories = [(6, 0, sup_cat_recs.ids)]

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

            if i % 100 == 0:
                self.env.cr.commit()
            print(
                f"{i} - Product {product.id_on_platform} percent expenses were updated."
            )

    def _update_percent_expenses(self, percent_expenses_ids):
        per_exp_recs = self.env["ozon.cost"].browse(percent_expenses_ids)
        names = [rec.name for rec in per_exp_recs]
        new_percent_expenses_ids = percent_expenses_ids
        for per_exp in self.percent_expenses:
            if per_exp.name not in names:
                new_percent_expenses_ids.append(per_exp.id)

        self.percent_expenses = [(6, 0, new_percent_expenses_ids)]

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

    def draw_plot_products(self):
        model_sale = self.env["ozon.sale"]

        time_now = datetime.now()

        records_current_year = {"dates": [], "num": []}
        records_last_year = {"dates": [], "num": []}

        for rec in self:
            records = model_sale.search([("product", "=", rec.id)])

            for record in records:
                if record.date.year == time_now.year:
                    records_current_year["dates"].append(
                        record.date.strftime("%Y-%m-%d")
                    )
                    records_current_year["num"].append(record.qty)

                elif record.date.year == time_now.year - 1:
                    records_last_year["dates"].append(record.date.strftime("%Y-%m-%d"))
                    records_last_year["num"].append(record.qty)

            endpoint = "http://django:8000/api/v1/draw_graph"
            payload = {
                "model": "products",
                "product_id": rec.id,
                "current": records_current_year,
                "last": records_last_year,
            }
            api_token = getenv("API_TOKEN_DJANGO")
            headers = {"Authorization": f"Token {api_token}"}
            response = requests.post(endpoint, json=payload, headers=headers)

            if response.status_code != 200:
                raise ValueError(f"{response.status_code}--{response.text}")

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

    def _compute_imgs_analysis_data_last_year(self):
        for rec in self:
            rec.imgs_html_analysis_data_last_year = False
            if rec.imgs_url_last_year:
                rec.imgs_html_analysis_data_last_year = (
                    f"<img src='{rec.imgs_url_last_year}' width='600'/>"
                )

    def _compute_imgs_analysis_data_this_year(self):
        for rec in self:
            rec.imgs_html_analysis_data_this_year = False
            if rec.imgs_url_this_year:
                rec.imgs_html_analysis_data_this_year = (
                    f"<img src='{rec.imgs_url_this_year}' width='600'/>"
                )

    def _compute_imgs_price_history_this_year(self):
        for rec in self:
            rec.imgs_html_price_history_this_year = False
            if rec.imgs_url_price_history_this_year:
                rec.imgs_html_price_history_this_year = (
                    f"<img src='{rec.imgs_url_price_history_this_year}' width='600'/>"
                )

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
                    if pc_rec.name == "Цена":
                        pc_rec.value = rec.price
                    elif pc_rec.name == "Прибыль":
                        pc_rec.value = rec.profit
                    elif pc_rec.name == "Идеальная прибыль":
                        pc_rec.value = rec.profit_ideal
                    elif pc_rec.name == "Разница между прибылью и идеальной прибылью":
                        pc_rec.value = rec.profit_delta
                    elif pc_rec.name == "Отклонение от прибыли":
                        pc_rec.value = rec.coef_profitability
            else:
                self.env["ozon.product_calculator"].create(
                    [
                        {
                            "name": "Цена",
                            "product_id": rec.id,
                            "value": rec.price,
                        },
                        {
                            "name": "Прибыль",
                            "product_id": rec.id,
                            "value": rec.profit,
                        },
                        {
                            "name": "Идеальная прибыль",
                            "product_id": rec.id,
                            "value": rec.profit_ideal,
                        },
                        {
                            "name": "Разница между прибылью и идеальной прибылью",
                            "product_id": rec.id,
                            "value": rec.profit_delta,
                        },
                        {
                            "name": "Отклонение от прибыли",
                            "product_id": rec.id,
                            "value": rec.coef_profitability,
                        },
                    ]
                )

    @api.onchange("pricing_strategy_ids")
    def onchange_pricing_stragegy_ids(self):
        prod_calc_ids = self.product_calculator_ids.ids
        prod_calc_recs = self.env["ozon.product_calculator"].browse(prod_calc_ids)
        if not self.pricing_strategy_ids:
            for prod_calc_rec in prod_calc_recs:
                prod_calc_rec.new_value = 0
            return

        # constants
        if self.trading_scheme in ["FBS", "FBS, FBO", ""]:
            total_expenses = (
                self.total_fbs_fix_expenses_max + self.total_fbs_percent_expenses
            )
        elif self.trading_scheme == "FBO":
            total_expenses = (
                self.total_fbo_fix_expenses_max + self.total_fbo_percent_expenses
            )
        prof_norm = self.profitability_norm.value if self.profitability_norm else 0.2

        # TODO: как считать новые значения, если применяется несколько стратегий?
        new_prices = []
        new_profits = []
        new_profit_ideals = []
        new_profit_deltas = []
        new_coef_profs = []
        for price_strategy in self.pricing_strategy_ids:
            strategy_value = price_strategy.value
            strategy_id = price_strategy.strategy_id

            if strategy_id == "lower_min_competitor":
                if self.competitors_with_price_ids:
                    comp_prices = self.competitors_with_price_ids.mapped("price")
                    min_comp_price = min(comp_prices)
                    new_price = round(min_comp_price * (1 - strategy_value), 2)

            if strategy_id == "profitability_norm":
                prof_norm = strategy_value
                if prof_norm == 0:
                    return
                new_price = total_expenses / (1 - prof_norm)

            new_profit = new_price - total_expenses
            new_profit_ideal = new_price * prof_norm
            new_profit_delta = new_profit - new_profit_ideal
            new_coef_profitability = round(new_profit_delta / new_profit_ideal, 2)

            new_prices.append(new_price)
            new_profits.append(new_profit)
            new_profit_ideals.append(new_profit_ideal)
            new_profit_deltas.append(new_profit_delta)
            new_coef_profs.append(new_coef_profitability)

        for prod_calc_rec in prod_calc_recs:
            if prod_calc_rec.name == "Цена":
                prod_calc_rec.new_value = mean(new_prices)
            elif prod_calc_rec.name == "Прибыль":
                prod_calc_rec.new_value = mean(new_profits)
            elif prod_calc_rec.name == "Идеальная прибыль":
                prod_calc_rec.new_value = mean(new_profit_ideals)
            elif prod_calc_rec.name == "Разница между прибылью и идеальной прибылью":
                prod_calc_rec.new_value = mean(new_profit_deltas)
            elif prod_calc_rec.name == "Отклонение от прибыли":
                prod_calc_rec.new_value = mean(new_coef_profs)

    def calculate(self):
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


class ProductCalculator(models.Model):
    _name = "ozon.product_calculator"
    _description = "Калькулятор лота"

    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    name = fields.Char(string="Параметр")
    value = fields.Float(string="Текущее значение")
    new_value = fields.Float(string="Новое значение")
