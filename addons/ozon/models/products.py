# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
from operator import itemgetter

from odoo import models, fields, api

from ..ozon_api import MIN_FIX_EXPENSES, MAX_FIX_EXPENSES
from ..helpers import (
    split_list,
    split_keywords,
    split_keywords_on_slash,
    remove_latin_characters,
)


class Product(models.Model):
    _name = "ozon.products"
    _description = "Лоты"

    categories = fields.Many2one("ozon.categories", string="Название категории")
    id_on_platform = fields.Char(string="ID на площадке", unique=True)
    full_categories = fields.Char(string="Наименоваие раздела")
    supplementary_categories = fields.One2many(
        "ozon.supplementary_categories",
        "product_id",
        string="Вспомогательные категории",
        copy=True,
        readonly=True,
    )
    products = fields.Many2one("retail.products", string="Товар")
    price = fields.Float(string="Актуальная цена", readonly=True)
    seller = fields.Many2one("retail.seller", string="Продавец")
    index_localization = fields.Many2one(
        "ozon.localization_index", string="Индекс локализации"
    )
    insurance = fields.Float(string="Страховой коэффициент, %")
    search_queries = fields.One2many(
        "ozon.search_queries", "product_id", string="Поисковые запросы"
    )
    trading_scheme = fields.Selection(
        [
            ("FBS", "FBS"),
            ("FBO", "FBO"),
            ("FBS, FBO", "FBS, FBO"),
            ("", ""),
        ],
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

    price_history_ids = fields.One2many(
        "ozon.price_history_competitors", "product_id", string="История цен конкурентов"
    )

    price_our_history_ids = fields.One2many(
        "ozon.price_history", "product_id", string="История цен"
    )
    stock = fields.Many2one("ozon.stock", string="Остатки товаров")
    stocks_fbs = fields.Integer(related="stock.stocks_fbs", store=True)
    stocks_fbo = fields.Integer(related="stock.stocks_fbo", store=True)
    is_selling = fields.Boolean(
        string="В продаже", compute="_get_is_selling", store=True, readonly=True
    )
    is_alive = fields.Boolean(
        string="Живой товар (в продаже и продавался за посл. 30 дней)",
        compute="_get_is_alive",
        store=True,
        readonly=True,
    )

    fix_expenses = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты",
        copy=True,
        readonly=True,
    )

    fix_expenses_min = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты минимальные",
        readonly=True,
        domain=[("name", "in", MIN_FIX_EXPENSES)],
    )
    total_fix_expenses_min = fields.Float(
        string="Итого", compute="_compute_total_fix_expenses_min", store=True
    )
    fix_expenses_max = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты максимальные",
        readonly=True,
        domain=[("name", "in", MAX_FIX_EXPENSES)],
    )
    total_fix_expenses_max = fields.Float(
        string="Итого", compute="_compute_total_fix_expenses_max", store=True
    )

    percent_expenses = fields.One2many(
        "ozon.cost",
        "product_id",
        string="Процент от продаж",
        copy=True,
        readonly=True,
    )

    total_percent_expenses = fields.Float(
        string="Итого", compute="_compute_total_percent_expenses", store=True
    )

    product_fee = fields.Many2one("ozon.product_fee", string="Комиссии товара Ozon")
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
    coef_profitability = fields.Float(
        string="Коэффициент прибыльности",
    )
    coef_profitability_group = fields.Char(
        string="Группа коэффициента прибыльности",
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

    @api.depends("price", "total_fix_expenses_max", "total_percent_expenses")
    def _compute_profit(self):
        for record in self:
            record.profit = (
                record.price
                - record.total_fix_expenses_max
                - record.total_percent_expenses
            )

    @api.depends("price")
    def _compute_profit_ideal(self):
        for record in self:
            record.profit_ideal = record.price * 0.2

    @api.depends("profit", "profit_ideal")
    def _compute_profit_delta(self):
        for record in self:
            record.profit_delta = record.profit - record.profit_ideal

    @api.depends("fix_expenses_min.price")
    def _compute_total_fix_expenses_min(self):
        for record in self:
            record.total_fix_expenses_min = sum(record.fix_expenses_min.mapped("price"))

    @api.depends("fix_expenses_max.price")
    def _compute_total_fix_expenses_max(self):
        for record in self:
            record.total_fix_expenses_max = sum(record.fix_expenses_max.mapped("price"))

    @api.depends("percent_expenses.price")
    def _compute_total_percent_expenses(self):
        for record in self:
            record.total_percent_expenses = sum(record.percent_expenses.mapped("price"))

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

    def _compute_coef_profitability(self):
        for product in self:
            price_history_record = self.env["ozon.price_history"].search(
                [
                    ("product", "=", product.id),
                    ("price", "=", product.price),
                ],
                limit=1,
                order="create_date desc",
            )
            product.coef_profitability = price_history_record.coef_profitability

    def _compute_coef_profitability_group(self):
        coefs = self.read(fields=["coef_profitability"])
        coefs = sorted(coefs, key=itemgetter("coef_profitability"))
        g1, g2, g3, g4, g5 = list(split_list(coefs, 5))
        for i, g in enumerate([g1, g2, g3, g4, g5]):
            g_min = round(g[0]["coef_profitability"], 2)
            g_max = round(g[-1]["coef_profitability"], 2)
            for item in g:
                prod = self.env["ozon.products"].search([("id", "=", item["id"])])
                prod.coef_profitability_group = f"Группа {i+1}: от {g_min} до {g_max}"

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

    @api.model
    def write(self, values, cr=None):
        if values.get("fix_expenses"):
            cost_price = self.env["retail.cost_price"].search(
                [("products", "=", cr["products"].id)],
                order="timestamp desc",
                limit=1,
            )

            fix_expense_record = self.env["ozon.fix_expenses"].create(
                {
                    "name": "Себестоимость товара",
                    "price": cost_price.price,
                    "discription": "Поиск себестоимости товара в 'Retail'",
                    "product_id": cr.id,
                }
            )
            values["fix_expenses"] = [fix_expense_record.id] + values["fix_expenses"]

        return super(Product, self).write(values)

    @api.depends("stocks_fbs", "stocks_fbo")
    def _get_is_selling(self):
        for record in self:
            if record.stocks_fbs > 0 or record.stocks_fbo > 0:
                record.is_selling = True
            else:
                record.is_selling = False

    @api.depends("is_selling", "sales_per_day_last_30_days")
    def _get_is_alive(self):
        for record in self:
            if record.is_selling or record.sales_per_day_last_30_days > 0:
                record.is_alive = True
            else:
                record.is_alive = False

    def update_coefs_and_groups(self):
        all_products = self.search([])
        # coefs
        all_products._compute_coef_profitability()
        all_products._compute_sales_per_day_last_30_days()
        # groups
        all_products._compute_coef_profitability_group()
        alive_products = self.search([("is_alive", "=", True)])
        not_alive_products = all_products - alive_products
        for rec in not_alive_products:
            rec.sales_per_day_last_30_days_group = ""
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
        cats_list = remove_latin_characters(cats_list)
        sup_cat_data = [{"name": cat, "product_id": self.id} for cat in cats_list]
        sup_cat_ids = self.env["ozon.supplementary_categories"].create(sup_cat_data)
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
            # добавить к нему уже имеющуюся запись "Процент комиссии за продажу"
            sale_percent_com_record = product.percent_expenses.search(
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
                limit=1,
            )
            if sale_percent_com_record:
                percent_expenses_records.append(sale_percent_com_record.id)

            product.percent_expenses = [(6, 0, percent_expenses_records)]

            if i % 100 == 0:
                self.env.cr.commit()
            print(
                f"{i} - Product {product.id_on_platform} percent expenses were updated."
            )
