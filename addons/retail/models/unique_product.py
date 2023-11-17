# -*- coding: utf-8 -*-

from odoo import models, fields, api


class UniqueProduct(models.Model):
    _name = 'retail.unique_product'
    _description = 'Unique product'

    products = fields.Many2one('retail.products', string='Наименование продукта')
    character = fields.Many2one(
        'retail.character', string='Характеристики товара'
    )
    seller = fields.Many2one('retail.seller', string='Продавец')
