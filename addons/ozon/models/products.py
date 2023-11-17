# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Product(models.Model):
    _name = 'ozon.products'
    _description = 'Лоты'

    categories = fields.Char(string='Название категории')
    id_on_platform = fields.Integer(string='ID на площадке')
    full_categories = fields.Char(string='Наименоваие раздела')
    
    products = fields.Many2one('retail.products', string='Товар')
    seller = fields.Many2one('retail.seller', string='Продавец')
    index_localization = fields.Many2one(
        'ozon.localization_index', string='Индекс локализации'
    )
    trading_scheme = fields.Selection(
        [
            ('FBS', 'FBS'),
            ('FBO', 'FBO'),
        ], 
        string='Схема торговли'
    )
    delivery_location = fields.Selection(
        [
            ('ППЦ', 'ППЦ/PC'),
            ('ПВЗ', 'ПВЗ/PP'),
            ('СЦ', 'СЦ/CS'),
        ],
        string='Пункт приема товара', 
        help=(
            'ППЦ - Пункт приема заказов (Pickup Center), '
            'ПВЗ - Пункт выдачи заказов (Pickup Point), '
            'СЦ - Сервисный центр (Service Center)'
        )
    )
