# -*- coding: utf-8 -*-

from odoo import models, fields, api


class LogisticsOzon(models.Model):
    _name = 'ozon.logistics_ozon'
    _description = 'Стоимость логистики'
    
    trading_scheme = fields.Selection(
        [
            ('FBS', 'FBS'),
            ('FBO', 'FBO'),
        ], 
        string='Схема торговли'
    )
    volume = fields.Float(string='Объем')
    price = fields.Float(string='Стоимость')
