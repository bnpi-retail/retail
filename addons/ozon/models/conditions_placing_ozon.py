# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ConditionsPlacingOzon(models.Model):
    _name = 'ozon.conditions_placing_ozon'
    _description = 'Условия размещения товара на Ozon'

    products = fields.Many2one('retail.products', string='Товар')
    seller = fields.Many2one('retail.seller', string='Продавец')
    type_of_stock = fields.Many2one('retail.stocks', string='Тип')

    delivery_location = fields.Selection([
        ('ППЦ', 'ППЦ'),
        ('ПВЗ', 'ПВЗ'),
        ('СЦ', 'СЦ'),
    ], string='Пункт Сдачи')
