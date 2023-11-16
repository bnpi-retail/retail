# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OzonFee(models.Model):
    _name = 'ozon.ozon_fee'
    _description = 'Комисии товара'

    name = fields.Char(string='Наименование комиссии')
    category = fields.Many2one('retail.categories', string='Название категории')
    type = fields.Selection([
        ('percent', 'Процент'),
        ('fix', 'Фиксированный'),
    ], string='Тип категории')
    value = fields.Float(string='Значние комиссии')
