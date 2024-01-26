from odoo import models, fields


class IndicatorSummary(models.Model):
    _name = 'ozon.products.indicator.summary'
    _description = 'Вывод по индикаторам для продукта(лота)'

    active = fields.Boolean(default=True)
    name = fields.Char(size=100)
    ozon_product_id = fields.Many2one('ozon.products')

