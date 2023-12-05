# -*- coding: utf-8 -*-

from odoo import models, fields, api


class LogisticsOzon(models.Model):
    _name = 'ozon.logistics_ozon'
    _description = 'Стоимость логистики'
    
    trading_scheme = fields.Selection([('FBS', 'FBS'),
                                       ('FBO', 'FBO')], 
                                        string='Схема торговли')
    volume = fields.Float(string='Объем, л')
    price = fields.Float(string='Стоимость, р.')


    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, 
                           f'{record.trading_scheme}, '
                           f'Объем = {record.volume}, '
                           f'Цена = {record.price}'))
        return result
    