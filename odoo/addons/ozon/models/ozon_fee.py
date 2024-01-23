# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OzonFee(models.Model):
    _name = 'ozon.ozon_fee'
    _description = 'Комисии товара'

    name = fields.Char(string='Наименование комиссии')
    value = fields.Float(string='Значние комиссии')
    category = fields.Many2one('ozon.categories', string='Название категории')
    
    type = fields.Selection([('percent', 'Процент'),
                             ('fix', 'Фиксированный')], 
                             string='Тип начисления')
    
    trading_scheme = fields.Selection([('FBS', 'FBS'),
                                       ('FBO', 'FBO'),
                                       ('rFBS', 'rFBS')],
                                       string='Схема торговли')
    
    delivery_location = fields \
        .Selection([('PC', 'ППЗ/PC'),
                    ('PP', 'ПВЗ/PP'),
                    ('SC', 'СЦ/SC'),
                    ('TSC', 'ТСЦ/TSC')],
                    string='Пункт приема товара', 
                    help=('ППЦ - Пункт приема заказов (Pickup Center), '
                        'ПВЗ - Пункт выдачи заказов (Pickup Point), '
                        'СЦ - Сервисный центр (Service Center)'))