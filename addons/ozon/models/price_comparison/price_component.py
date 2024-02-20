from odoo import models, fields, api


class PriceComponent(models.Model):
    _name = "ozon.price_component"
    _description = "Компонент цены"

    name = fields.Char(string="Название")