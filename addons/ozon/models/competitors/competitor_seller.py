from odoo import models, fields, api
from odoo.exceptions import UserError


class CompetitorSeller(models.Model):
    _name = "ozon.competitor_seller"
    _description = "Магазин-конкурент"

    trade_name = fields.Char(string='Торговое название')
    is_my_shop = fields.Boolean(readonly=True)

    products_competitors_ids = fields.One2many("ozon.products_competitors", 
                                               "competitor_seller_id", string="Товары")

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
        our_sellers = self.env["retail.seller"].search([])
        for record_vals in vals_list:
            competitor_trade_name = record_vals.get('trade_name')
            if competitor_trade_name and isinstance(competitor_trade_name, str):
                competitor_trade_name = competitor_trade_name.lower()
                for seller in our_sellers:
                    trade_name: str = seller.trade_name
                    trade_name = trade_name.lower()
                    if trade_name == competitor_trade_name:
                        record_vals['trade_name'] = trade_name + '_'

        return super().create(vals_list)

    def open_product_competitors_tree_view(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Товары конкурента",
            "view_mode": "tree,form",
            "res_model": "ozon.products_competitors",
            "domain": [("competitor_seller_id", "=", self.id)],
            "context": {"create": False}
        }