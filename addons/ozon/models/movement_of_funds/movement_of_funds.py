# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MovementOfFunds(models.Model):
    _name = 'ozon.movement_of_funds'
    _description = 'Движение средств'

    timestamp = fields.Date(string='Дата импорта', 
                            default=fields.Date.today,
                            readonly=True)
    product = fields.Many2one('ozon.products', string='Лот')
    status = fields.Selection([
        ('positive', 'Приход'),
        ('negative', 'Расход'),
    ], string='Тип учета')

    number = fields.Float(string='Количество, ед.')
    amount_of_money = fields.Float(string='Сумма, р.')
    categorie = fields.Selection([
        ('sell', 'Продажа'),
        ('treatment', 'Обработка'),
        ('insurance', 'Страховка'),
    ], string='Категория')


    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, f'{record.timestamp}, {record.categorie}, {record.product.products.name}'))
        return result
