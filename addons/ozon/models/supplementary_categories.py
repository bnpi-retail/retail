# # -*- coding: utf-8 -*-

from odoo import models, fields, api


class Categories(models.Model):
    _name = "ozon.supplementary_categories"
    _description = "Вспомогательные категории Ozon"

    name = fields.Char(string="Название")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
