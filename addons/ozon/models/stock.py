# -*- coding: utf-8 -*-

from email.policy import default
from odoo import models, fields, api


class ProductStock(models.Model):
    _name = "ozon.stock"
    _description = "Остатки товаров"

    product = fields.Many2one("ozon.products", string="Товар Ozon")
    timestamp = fields.Date(string='Дата', default=fields.Date.today)
    stocks_fbs = fields.Integer(string="Остатки FBS")
    stocks_reserved_fbs = fields.Integer(string="Зарезервирово остатков FBS")

    stocks_fbo = fields.Integer(string="Остатки FBO")
    _prod_id = fields.Integer(string="product_id", readonly=True)

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