# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Product(models.Model):
    _name = 'ozon.products'
    _description = 'Товары Ozon'

    product_id = fields.Integer(string='ID товара на Ozon')
    product = fields.Many2one('retail.products', string='Товар')