# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Warehouse(models.Model):
    _name = "ozon.warehouse"
    _description = "Склад Ozon"

    name = fields.Char(string="Название")
    w_id = fields.Char(string="Идентификатор")
