# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CountPrice(models.Model):
    _name = 'retail.count_price'
    _description = 'Расчет цены'
    
    unique_product = fields.Many2one(
        'retail.unique_product', string="Продукт из 'ID продукта'"
    )
    provider = fields.Char(string='Поставщик')
    number = fields.Float(string='Объем товаров')

    def apply_product(self) -> bool:
        count_price_id = self.id
        count_price_obj = self.env['retail.count_price'].search([('id', '=', count_price_id)])

        price = 0

        price_history = self.env['retail.price_history']
        price_history.create({
            'price': price,
            'unique_product': count_price_obj.unique_product,
            'provider': count_price_obj.provider,
            'number': count_price_obj.number,
        })
        return True


class Costs(models.Model):
    _name = 'retail.cost'
    _description = 'Затраты/Приходы'

    name = fields.Char(string='Наименование затрат')
    price = fields.Float(string='Значение', default=0)
    price_history_id = fields.Many2one(
        'retail.price_history', string='ID истории цены'
    )


class PriceHistory(models.Model):
    _name = 'retail.price_history'
    _description = 'История цен'
    
    price = fields.Float(string='Цена', readonly=True)
    unique_product = fields.Many2one(
        'retail.unique_product', string="Продукт из 'ID продукта'"
    )
    provider = fields.Char(string='Поставщик')
    timestamp = fields.Date(
        string='Дата', default=fields.Date.today, readonly=True
    )
    number = fields.Float(string='Объем товаров')
    costs = fields.One2many(
        'retail.cost', 'price_history_id', string='Затраты/Приходы', 
        copy=True
    )
