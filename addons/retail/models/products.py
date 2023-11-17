# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Product(models.Model):
    _name = 'retail.products'
    _description = 'Продукты'

    name = fields.Char(string='Наименование товара')
    description = fields.Char(string='Описание товара')
    
    length = fields.Float(string='Длина')
    width = fields.Float(string='Ширина')
    height = fields.Float(string='Высота')
    weight = fields.Float(string='Вес')
    volume = fields.Float(string='Объем', compute='_compute_volume', store=True)

    @api.depends('length', 'width', 'height')
    def _compute_volume(self):
        for record in self:
            record.volume = record.length * record.width * record.height