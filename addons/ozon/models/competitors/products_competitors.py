# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductCompetitors(models.Model):
    _name = 'ozon.products_competitors'
    _description = 'История цен конкуренты'
    
    id_product = fields.Char(string='Id продукта на Ozon')
    
    name = fields.Char(string='Наименование продукта')

    url = fields.Char(string='URL товара', widget="url", 
                      help='Укажите ссылку на товар в поле')

    product = fields.Many2one('ozon.products', string='Лот')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result