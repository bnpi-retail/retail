from odoo import models, fields


class ProductCompetitorSale(models.Model):
    _name = "ozon.products_competitors.sale"
    _description = 'Продажи товара-конкурента за период'

    period_from = fields.Date()
    period_to = fields.Date()
    category_lvl3 = fields.Char()
    orders_qty = fields.Integer()
    orders_avg_price = fields.Float()
    orders_sum = fields.Float()
    revenue_share_percentage = fields.Float()
    retail_seller_id = fields.Many2one('retail.seller', string="Продавец")
    ozon_products_competitors_id = fields.Many2one("ozon.products_competitors")
    ozon_report_category_market_share = fields.Many2one("ozon.report_category_market_share")
