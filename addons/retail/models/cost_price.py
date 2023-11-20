# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CostPrice(models.Model):
    _name = 'retail.cost_price'
    _description = 'Cost of price'

    products = fields.Many2one('retail.products', string='Наменование товар')
    seller = fields.Many2one('retail.seller', string='Продавец')
    price = fields.Float(string='Закупочная стоимость')
    timestamp = fields.Date(string='Дата', 
                            default=fields.Date.today, readonly=True)
    

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, record.products.name))
        return result