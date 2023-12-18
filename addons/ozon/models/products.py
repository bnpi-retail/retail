# -*- coding: utf-8 -*-

from odoo import models, fields, api

from ..ozon_api import MIN_FIX_EXPENSES, MAX_FIX_EXPENSES


class Product(models.Model):
    _name = "ozon.products"
    _description = "Лоты"

    categories = fields.Many2one("ozon.categories", string="Название категории")
    id_on_platform = fields.Char(string="ID на площадке", unique=True)
    full_categories = fields.Char(string="Наименоваие раздела")
    products = fields.Many2one("retail.products", string="Товар")
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

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.products.name))
        return result

    @api.depends("price_our_history_ids.price")
    def _compute_price_history_values(self):
        for product in self:
            product.price_history_values = [
                (record.timestamp, record.price)
                for record in product.price_our_history_ids
            ]

    @api.model
    def create(self, values):
        existing_record = self.search(
            [("id_on_platform", "=", values.get("id_on_platform"))]
        )
        if existing_record:
            return existing_record

        return super(Product, self).create(values)

    @api.model
    def write(self, values, cr):
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
