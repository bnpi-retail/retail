# # -*- coding: utf-8 -*-

from odoo import models, fields, api


class Categories(models.Model):
    _name = "ozon.supplementary_categories"
    _description = "Вспомогательные категории Ozon"

    name = fields.Char(string="Название", readonly=True)
    sc_id = fields.Integer(string="Идентификатор", readonly=True)

    category_manager = fields.Many2one("res.users")
