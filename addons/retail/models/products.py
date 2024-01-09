import uuid

from datetime import datetime, time, timedelta
from odoo import models, fields, api, exceptions


class Product(models.Model):
    _name = "retail.products"
    _description = "Продукты"

    name = fields.Char(string="Наименование товара")
    description = fields.Text(string="Описание товара")
    keywords = fields.Text(string="Ключевые слова")
    product_id = fields.Char(string="Артикул", unique=True, readonly=True)

    length = fields.Float(string="Длина, дм")
    width = fields.Float(string="Ширина, дм")
    height = fields.Float(string="Высота, дм")
    weight = fields.Float(string="Вес, кг")
    volume = fields.Float(string="Объем, л", compute="_compute_volume", store=True)

    cost_prices = fields.One2many(
        "retail.cost_price", "product_id", string="Себестоимость"
    )
    total_cost_price = fields.Float(
        string="Итого", compute="_compute_total_cost_price", store=True
    )

    get_cost_price_count = fields.Integer(compute="compute_cost_price")

    @api.depends("cost_prices", "cost_prices.price")
    def _compute_total_cost_price(self):
        for record in self:
            record.total_cost_price = sum(record.cost_prices.mapped("price"))

    @api.depends("cost_prices")
    def compute_cost_price(self):
        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90)

        for record in self:
            record.get_cost_price_count = self.env["retail.cost_price"].search_count(
                [
                    ("product_id", "=", record.id),
                    ("timestamp", ">=", three_months_ago.strftime("%Y-%m-%d %H:%M:%S")),
                ]
            )

    def get_cost_price(self):
        self.ensure_one()

        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90)

        return {
            "type": "ir.actions.act_window",
            "name": "История себестоимости",
            "view_mode": "tree,graph",
            "res_model": "retail.cost_price",
            "domain": [
                ("products", "=", self.id),
                ("timestamp", ">=", three_months_ago.strftime("%Y-%m-%d %H:%M:%S")),
            ],
            "context": {
                "create": False,
                "views": [(False, "tree"), (False, "form"), (False, "graph")],
                "graph_mode": "line",
            },
        }

    @api.depends("length", "width", "height")
    def _compute_volume(self):
        for record in self:
            record.volume = record.length * record.width * record.height

    @api.model
    def create(self, values):
        existing_record = self.search(
            [("product_id", "=", values.get("product_id"))], limit=1
        )
        if existing_record:
            return existing_record

        values["volume"] = values["length"] * values["width"] * values["height"]
        return super(Product, self).create(values)
