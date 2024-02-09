from odoo import models, fields


class CompetitorSeller(models.Model):
    _name = "ozon.competitor_seller"
    _description = "Магазин-конкурент"

    trade_name = fields.Char(string='Торговое название')
    is_my_shop = fields.Char(default=False)
