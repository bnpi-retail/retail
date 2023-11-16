# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Stocks(models.Model):
    _name = 'retail.stocks'
    _description = 'Склады'

    name = fields.Char(string='Наименование складов')