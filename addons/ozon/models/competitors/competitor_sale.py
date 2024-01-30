from odoo import models, fields


class ProductCompetitorSale(models.Model):
    _name = "ozon.products_competitors.sale"
    _description = 'Продажи товара-конкурента за период'

    period_from = fields.Date()
    period_to = fields.Date()
    ozon_products_competitors_id = fields.Many2one()
    category_lvl3 = fields.Char()
    orders_qty = fields.Integer()
    orders_sum = fields.Float()
