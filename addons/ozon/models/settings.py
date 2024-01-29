# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Settings(models.Model):
    _name = "ozon.settings"
    _description = "Настройки Ozon"

    name = fields.Selection(
        [
            ("OZON_API_KEY", "Ozon API-ключ"),
            ("MP_STATS_TOKEN", "MPStats токен"),
        ],
        string="Ключ",
    )
    value = fields.Char(string="Значение")
