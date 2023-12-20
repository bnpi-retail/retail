# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
from odoo import models, fields, api

from ..ozon_api import MIN_FIX_EXPENSES, MAX_FIX_EXPENSES
from ..helpers import split_list


class Product(models.Model):
    _name = "ozon.products"
    _description = "Лоты"

    categories = fields.Many2one("ozon.categories", string="Название категории")
    id_on_platform = fields.Char(string="ID на площадке", unique=True)
    full_categories = fields.Char(string="Наименоваие раздела")
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
        coefs = self.search([]).read(fields=["sales_per_day_last_30_days"])
        coefs = sorted([round(i["sales_per_day_last_30_days"], 2) for i in coefs])

        g1, g2, g3, g4, g5 = list(split_list(coefs, 5))
        for product in self:
            coef = round(product.sales_per_day_last_30_days, 2)
            if coef <= g1[-1]:
                product.sales_per_day_last_30_days_group = (
                    f"Группа 1: от {g1[0]} до {g1[-1]}"
                )
            elif g2[0] <= coef <= g2[-1]:
                product.sales_per_day_last_30_days_group = (
                    f"Группа 2: от {g2[0]} до {g2[-1]}"
                )
            elif g3[0] <= coef <= g3[-1]:
                product.sales_per_day_last_30_days_group = (
                    f"Группа 3: от {g3[0]} до {g3[-1]}"
                )
            elif g4[0] <= coef <= g4[-1]:
                product.sales_per_day_last_30_days_group = (
                    f"Группа 4: от {g4[0]} до {g4[-1]}"
                )
            elif coef >= g5[0]:
                product.sales_per_day_last_30_days_group = (
                    f"Группа 5: от {g5[0]} до {g5[-1]}"
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
        coefs = self.search([]).read(fields=["coef_profitability"])
        coefs = sorted([round(i["coef_profitability"], 2) for i in coefs])

        g1, g2, g3, g4, g5 = list(split_list(coefs, 5))
        for product in self:
            coef = round(product.coef_profitability, 2)
            if coef <= g1[-1]:
                product.coef_profitability_group = f"Группа 1: от {g1[0]} до {g1[-1]}"
            elif g2[0] <= coef <= g2[-1]:
                product.coef_profitability_group = f"Группа 2: от {g2[0]} до {g2[-1]}"
            elif g3[0] <= coef <= g3[-1]:
                product.coef_profitability_group = f"Группа 3: от {g3[0]} до {g3[-1]}"
            elif g4[0] <= coef <= g4[-1]:
                product.coef_profitability_group = f"Группа 4: от {g4[0]} до {g4[-1]}"
            elif coef >= g5[0]:
                product.coef_profitability_group = f"Группа 5: от {g5[0]} до {g5[-1]}"

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

    def update_coefs_and_groups(self):
        all_records = self.search([])
        all_records._compute_coef_profitability()
        all_records._compute_coef_profitability_group()
        all_records._compute_sales_per_day_last_30_days()
        # TODO: какие товары сегментируем на группы по продажам за посл. 30 дней?
        # все товары? только активные? только те, у которых были продажи за посл. 30 дней?
        all_records._compute_sales_per_day_last_30_days_group()

        # inactive_records = self.search([("is_selling", "=", False)])
        # for rec in inactive_records:
        #     rec.sales_per_day_last_30_days_group = ""

        # active_records = self.search([("is_selling", "=", True)])
        # active_records._compute_sales_per_day_last_30_days_group()
