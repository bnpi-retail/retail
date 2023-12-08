# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PriceHistoryCompetitors(models.Model):
    _name = 'ozon.price_history_competitors'
    _description = 'История цен конкурентов'

    timestamp = fields.Date(string='Дата', 
                            default=fields.Date.today,
                            readonly=True)
    
    product_competitors = fields.Many2one('ozon.products_competitors',
                                          string='Товар конкурента')
    
    price = fields.Float(string='Цена')

    product_id = fields.Many2one('ozon.products', string='Лот')

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
    
    @api.model
    def create(self, values):
        record = super(PriceHistoryCompetitors, self).create(values)

        product_record = record.product_competitors.product
        product_record.write({'price_history_ids': [(4, record.id)]})

        return record