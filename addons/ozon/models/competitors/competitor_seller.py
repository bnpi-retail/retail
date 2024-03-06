from odoo import models, fields, api
from odoo.exceptions import UserError


class CompetitorSeller(models.Model):
    _name = "ozon.competitor_seller"
    _description = "Магазин-конкурент"

    trade_name = fields.Char(string='Торговое название')
    is_my_shop = fields.Boolean(readonly=True)

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.trade_name))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        competitor_trade_name = vals_list.get('trade_name')
        if competitor_trade_name and isinstance(competitor_trade_name, str):
            competitor_trade_name = competitor_trade_name.lower()
            our_sellers = self.env["retail.seller"].search([])
            for seller in our_sellers:
                trade_name: str = seller.trade_name
                trade_name = trade_name.lower()
                if trade_name == competitor_trade_name:
                    vals_list['trade_name'] = trade_name + '_'

        return super().create(vals_list)
