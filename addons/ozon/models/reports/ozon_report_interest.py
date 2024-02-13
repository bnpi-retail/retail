from odoo import models, fields


class OzonReportInterest(models.Model):
    _name = "ozon.report.interest"
    _description = "Отчет по соотношению интереса к продукту и продажам"

    ozon_categories_id = fields.Many2one('ozon.categories')

    first_period_from = fields.Date()
    first_period_to = fields.Date()

    second_period_from = fields.Date()
    second_period_to = fields.Date()

    def action_calculate_interest_report(self):
        pass