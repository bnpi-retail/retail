# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Seller(models.Model):
    _name = 'retail.seller'
    _description = 'Cost on platform'

    name = fields.Char(string='Имя продовца')
    ogrn = fields.Float(string='ОГРН', unique=True)
    fee = fields.Float(string='Налогообложение, %')