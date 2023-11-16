# -*- coding: utf-8 -*-

from odoo import models, fields, api


class UniqueProduct(models.Model):
    _name = 'retail.unique_product'
    _description = 'Unique product'

    product_id = fields.Float(string='ID товара')
    products = fields.Many2one('retail.products', string='Наименование продукта')
    character = fields.Many2one(
        'retail.character', string='Характеристики товара'
    )
    seller = fields.Many2one('retail.seller', string='Продавец')
    platform = fields.Many2one('retail.name_market', string='Платформа')
