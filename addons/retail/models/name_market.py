# -*- coding: utf-8 -*-

from odoo import models, fields, api


class NameMarket(models.Model):
    _name = 'retail.name_market'
    _description = 'Площадка'

    name = fields.Char(string='Название площадки')
