# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Product(models.Model):
    _name = 'retail.products'
    _description = 'Продукты'

    name = fields.Char(string='Наименование товара')
