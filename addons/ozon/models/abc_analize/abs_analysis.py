from odoo import models, fields


class AbcAnalysis(models.Model):
    _name = "ozon.abc_analysis"
    _description = "ABC Анализ"

    ozon_categories_ids = fields.Many2one('ozon.categories')
    period_from = fields.Date()
    period_to = fields.Date()

    ozon_products_ids = fields.Many2many("ozon.products")

    def action_do_abc_analysis(self):
        pass
