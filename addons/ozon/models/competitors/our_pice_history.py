# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HistoryOurPrice(models.Model):
    _name = 'ozon.our_price_history'
    _description = 'История наших цен'

    timestamp = fields.Date(string='Дата', 
                            default=fields.Date.today,
                            readonly=True)
    
    product = fields.Many2one('ozon.products', string='Лот')
    
    price = fields.Float(string='Наша цена')


    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id,
                           f'{record.timestamp},  '
                           f'{record.product.products.name}'))
        return result