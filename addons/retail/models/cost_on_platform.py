# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CostOnPlatform(models.Model):
    _name = 'retail.cost_on_platform'
    _description = 'Cost on platform'

    products = fields.Many2one('retail.products', string='Товар')
    seller = fields.Many2one('retail.seller', string='Продавец')
    platofrm = fields.Many2one('retail.name_market', string='Платформа')
    price = fields.Float(string='Стоимость на маркет плейсе, р.')

    timestamp = fields.Date(
        string='Дата', default=fields.Date.today
    )