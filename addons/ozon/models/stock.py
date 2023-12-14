# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductStock(models.Model):
    _name = "ozon.stock"
    _description = "Остатки товаров"

    product = fields.Many2one("ozon.products", string="Товар Ozon")
    stocks_fbs = fields.Integer(string="Остатки FBS")
    stocks_fbo = fields.Integer(string="Остатки FBO")
    _prod_id = fields.Integer(string="product_id", readonly=True)
