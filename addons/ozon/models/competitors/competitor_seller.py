from odoo import models, fields


class CompetitorSeller(models.Model):
    _name = "ozon.competitor_seller"
    _description = "Магазин-конкурент"

    trade_name = fields.Char(string='Торговое название')
    is_my_shop = fields.Char(default=False)

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.trade_name))
        return result