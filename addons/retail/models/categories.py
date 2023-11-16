# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Categories(models.Model):
    _name = 'retail.categories'
    _description = 'Categories of Market'

    name_categories = fields.Char(string='Название категории')
    name_platform = fields.Many2one(
        'retail.name_market', string='Название платформы'
    )