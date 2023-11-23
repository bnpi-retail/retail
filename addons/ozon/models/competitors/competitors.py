# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Competitors(models.Model):
    _name = 'ozon.competitors'
    _description = 'История цен конкуренты'

    timestamp = fields.Date(string='Дата', 
                            default=fields.Date.today,
                            readonly=True)
    
    product = fields.Many2one('ozon.products', string='Лот')

    name = fields.Char(string='Название конкурента')
    
    price = fields.Float(string='Цена конкурента')


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