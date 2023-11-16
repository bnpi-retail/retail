# -*- coding: utf-8 -*-

from odoo import models, fields, api


class LogisticsOzon(models.Model):
    _name = 'ozon.logistics_ozon'
    _description = 'Стоимость логистики'

    type_of_stock = fields.Many2one('retail.stocks', string='Тип')
    volume = fields.Float(string='Объем')
    price = fields.Float(string='Стоимость')
