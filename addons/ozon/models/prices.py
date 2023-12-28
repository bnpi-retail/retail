# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from email.policy import default
from odoo import models, fields, api

from ..ozon_api import MAX_FIX_EXPENSES_FBO, MAX_FIX_EXPENSES_FBS


class CountPrice(models.Model):
    """
    Model for select products and count price
    """

    _name = "ozon.count_price"
    _description = "Акт расчета цен"

    product = fields.Many2many("ozon.products", string="Товар")
    provider = fields.Many2one("retail.seller", string="Продавец")

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            seller = record.provider.name
            if not seller:
                seller = "Отсутствует"
            result.append(
                (record.id, f"Продавец: {seller}, Позиций: {len(record.product)}")
            )
        return result

    def create_cost_fix(self, name: str, price: float, discription: str) -> int:
        """
        Create record in 'ozon.fix_expenses' model
        """
        cost_price = self.env["ozon.fix_expenses"]
        return cost_price.create(
            {
                "name": name,
                "price": price,
                "discription": discription,
            }
        ).id

    def create_cost(self, name: str, price: float, discription: str) -> int:
        """
        Create record in 'ozon.cost' model
        """
        cost_price = self.env["ozon.cost"]
        return cost_price.create(
            {
                "name": name,
                "price": price,
                "discription": discription,
            }
        ).id

    def select_cost_price(self, product) -> int:
        """
        Select cost price of product
        """
        cost_price = (
            self.env["retail.cost_price"]
            .search(
                [
                    ("id", "=", product.products.id),
                    ("seller.id", "=", product.seller.id),
                ],
                limit=1,
                order="timestamp desc",
            )
            .price
        )
        return cost_price

    def count_price(self, product) -> int:
        """
        Count price of product
        """
        return 0

    def apply_product(self) -> bool:
        """
        Function for count price
        """
        price_history = self.env["ozon.price_history"]

        for count_price_obj in self:
            for product in count_price_obj.product:
                price = (
                    self.env["ozon.price_history"]
                    .search(
                        [
                            ("product", "=", product.products.id),
                        ],
                        limit=1,
                    )
                    .price
                )

                product_info = product.products

                info = {
                    "cost_price_product": self.select_cost_price(product),
                    # Info in linked model 'product'
                    "name": product_info.name,
                    "description": product_info.description,
                    "product_id": product_info.product_id,
                    "length": product_info.length,
                    "width": product_info.width,
                    "height": product_info.height,
                    "weight": product_info.weight,
                    "volume": product_info.volume,
                    # Info in self model
                    "categories": product.categories,
                    "id_on_platform": product.id_on_platform,
                    "full_categories": product.full_categories,
                    "products": product.products,
                    "index_localization": product.index_localization,
                    "trading_scheme": product.trading_scheme,
                    "delivery_location": product.delivery_location,
                }

                price_history.create(
                    {
                        "product": product.products.id,
                        "provider": count_price_obj.provider.id,
                        "price": price,
                        # 'price': 0,
                    }
                )
        return True


class FixExpenses(models.Model):
    _name = "ozon.fix_expenses"
    _description = "Фиксированные затраты"

    name = fields.Char(string="Наименование")
    price = fields.Float(string="Значение")
    discription = fields.Text(string="Описание")
    price_history_id = fields.Many2one("ozon.price_history", string="История цен")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")

    def create_from_ozon_product_fee(self, product_id, price_history_id):
        product_fee = self.env["ozon.product_fee"].search(
            [("product", "=", product_id)]
        )
        field_names = [
            field
            for field in product_fee.fields_get_keys()
            if field
            not in [
                "product",
                "sales_percent_fbo",
                "sales_percent_fbs",
                "sales_percent",
                "id",
                "__last_update",
                "display_name",
                "create_uid",
                "create_date",
                "write_uid",
                "write_date",
            ]
        ]
        fieldnames_and_strings = [
            (k, v.string) for k, v in product_fee._fields.items() if k in field_names
        ]
        data = []
        for field, string in fieldnames_and_strings:
            rec = {
                "name": string,
                "price": product_fee[field],
                "discription": "",
                "price_history_id": price_history_id,
            }
            data.append(rec)

        recs = self.create(data)

        return recs.ids


class Costs(models.Model):
    _name = "ozon.cost"
    _description = "Процент от продаж"

    name = fields.Char(string="Наименование")
    price = fields.Float(string="Значение")
    discription = fields.Text(string="Описание")
    price_history_id = fields.Many2one("ozon.price_history", string="История цен")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")

    def create_from_ozon_product_fee(self, product_id, price_history_id, price):
        product_fee = self.env["ozon.product_fee"].search(
            [("product", "=", product_id)]
        )
        field_names = [
            field
            for field in product_fee.fields_get_keys()
            if field
            in [
                "sales_percent_fbo",
                "sales_percent_fbs",
            ]
        ]
        fieldnames_and_strings = [
            (k, v.string) for k, v in product_fee._fields.items() if k in field_names
        ]
        data = []
        for field, string in fieldnames_and_strings:
            rec = {
                "name": string,
                "price": round(price * product_fee[field] / 100, 2),
                "discription": f"{product_fee[field]}%",
                "price_history_id": price_history_id,
            }
            data.append(rec)

        recs = self.create(data)

        return recs.ids


class PriceHistory(models.Model):
    _name = "ozon.price_history"
    _description = "История цен"

    product = fields.Many2one("ozon.products", string="Товар")
    provider = fields.Many2one("retail.seller", string="Продавец")
    price = fields.Float(string="Установленная цена", readonly=True)
    competitors = fields.One2many(
        "ozon.name_competitors",
        "pricing_history_id",
        string="Цены конкурентов",
        copy=True,
    )

    previous_price = fields.Float(string="Предыдущая цена", readonly=True)
    timestamp = fields.Date(string="Дата", default=fields.Date.today, readonly=True)

    @api.model
    def _change_fix_expenses_domain(self):
        if self.product.trading_scheme == "FBS":
            domain = [("name", "in", MAX_FIX_EXPENSES_FBS)]
        elif self.product.trading_scheme == "FBO":
            domain = [("name", "in", MAX_FIX_EXPENSES_FBO)]
        else:
            domain = []
        return domain

    fix_expenses = fields.One2many(
        "ozon.fix_expenses",
        "price_history_id",
        string="Фиксированные затраты максимальные",
        copy=True,
        readonly=True,
        domain=_change_fix_expenses_domain,
    )

    total_cost_fix = fields.Float(
        string="Итого фикс.затраты",
        compute="_compute_total_cost_fix",
        store=True,
    )
    costs = fields.One2many(
        "ozon.cost",
        "price_history_id",
        string="Процент от продаж",
        copy=True,
        readonly=True,
    )
    total_cost_percent = fields.Float(
        string="Итого проц.затраты",
        related="product.total_percent_expenses",
        store=True,
    )

    profit = fields.Float(
        string="Прибыль от установленной цены", compute="_compute_profit", store=True
    )
    profit_ideal = fields.Float(
        string="Идеальная прибыль", compute="_compute_profit_ideal", store=True
    )
    profit_delta = fields.Float(
        string="Разница между прибылью и идеальной прибылью",
        compute="_compute_profit_delta",
        store=True,
    )
    coef_profitability = fields.Float(
        string="Коэффициент прибыльности",
        compute="_compute_coef_profitability",
        store=True,
    )

    product_id = fields.Many2one("ozon.products", string="Лот")

    @api.depends("fix_expenses.price")
    def _compute_total_cost_fix(self):
        for record in self:
            record.total_cost_fix = sum(record.fix_expenses.mapped("price"))

    @api.depends("price", "total_cost_fix", "total_cost_percent")
    def _compute_profit(self):
        for record in self:
            record.profit = (
                record.price - record.total_cost_fix - record.total_cost_percent
            )

    @api.depends("price")
    def _compute_profit_ideal(self):
        for record in self:
            record.profit_ideal = record.price * 0.2

    @api.depends("profit", "profit_ideal")
    def _compute_profit_delta(self):
        for record in self:
            record.profit_delta = record.profit - record.profit_ideal

    @api.depends("profit", "profit_ideal")
    def _compute_coef_profitability(self):
        for record in self:
            record.coef_profitability = record.profit / record.profit_ideal

    @api.model
    def create(self, values):
        if values.get("fix_expenses"):
            ozon_product_id = values["product"]
            cost_price_record = self.env["ozon.fix_expenses"].search(
                [
                    ("product_id", "=", ozon_product_id),
                    ("name", "=", "Себестоимость товара"),
                ],
                order="create_date desc",
                limit=1,
            )
            values["fix_expenses"] = [cost_price_record.id] + values["fix_expenses"]

        record = super(PriceHistory, self).create(values)
        product = record.product
        product.write({"price_our_history_ids": [(4, record.id)]}, product)
        return record

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            id = record.id
            result.append(
                (id, f"{record.timestamp},  " f"{record.product.products.name}")
            )
        return result
