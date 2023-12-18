# -*- coding: utf-8 -*-
from datetime import timedelta
from email.policy import default
from odoo import models, fields, api

from ..ozon_api import MIN_FIX_EXPENSES, MAX_FIX_EXPENSES


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


class Costs(models.Model):
    _name = "ozon.cost"
    _description = "Процент от продаж"

    name = fields.Char(string="Наименование")
    price = fields.Float(string="Значение")
    discription = fields.Text(string="Описание")
    price_history_id = fields.Many2one("ozon.price_history", string="История цен")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")


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

    total_cost_fix = fields.Float(
        string="Итого фикс.затраты",
        related="product.total_fix_expenses_max",
        store=True,
    )
    total_cost_percent = fields.Float(
        string="Итого проц.затраты",
        related="product.total_percent_expenses",
        store=True,
    )
    fix_expenses = fields.One2many(
        "ozon.fix_expenses",
        "price_history_id",
        string="Фиксированные затраты максимальные",
        copy=True,
        readonly=True,
        domain=[("name", "in", MAX_FIX_EXPENSES)],
    )
    costs = fields.One2many(
        "ozon.cost",
        "price_history_id",
        string="Процент от продаж",
        copy=True,
        readonly=True,
    )

    our_price = fields.Float(
        string="Расчетная цена", compute="_compute_our_price", store=True
    )

    ideal_price = fields.Float(
        string="Идеальная цена", compute="_compute_ideal_price", store=True
    )

    profit = fields.Float(
        string="Прибыль от расчетной цены", compute="_compute_profit", store=True
    )

    custom_our_price = fields.Float(string="Своя расчетная цена", default=0)

    product_id = fields.Many2one("ozon.products", string="Лот")

    @api.depends("total_cost_fix")
    def _compute_ideal_price(self):
        for record in self:
            record.ideal_price = 2 * record.total_cost_fix

    @api.depends("ideal_price")
    def _compute_our_price(self):
        for record in self:
            if record.custom_our_price != 0:
                record.our_price = record.custom_our_price
            else:
                record.our_price = record.ideal_price

    @api.depends("our_price", "total_cost_fix", "total_cost_percent")
    def _compute_profit(self):
        for record in self:
            total = record.our_price - record.total_cost_fix - record.total_cost_percent
            record.profit = total

    @api.model
    def create(self, values):
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
