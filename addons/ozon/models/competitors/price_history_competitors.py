# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PriceHistoryCompetitors(models.Model):
    _name = 'ozon.price_history_competitors'
    _description = 'История цен конкурентов'

    timestamp = fields.Date(string='Дата', default=fields.Date.today)
    
    product_competitors = fields.Many2one('ozon.products_competitors',
                                          string='Товар конкурента')
    
    price = fields.Float(string='Цена')
    price_with_card = fields.Float(string='Цена по карте Ozon')
    price_without_sale = fields.Float(string='Цена без скидки')

    sales = fields.Integer(string='Продажи')
    balance = fields.Integer(string='Остатки')
    revenue = fields.Float(string='Выручка', compute='_compute_revenue')

    rating = fields.Integer(string='Рейтинг')
    comments = fields.Integer(string='Комментарии')
    requests = fields.Integer(string='Запросы')

    @api.depends('price_with_card', 'sales')
    def _compute_revenue(self):
        for record in self:
            record.revenue = record.price * record.sales

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id,
                           f'{record.timestamp},  '
                           f'{record.product_competitors.product.products.name}'))
        return result
