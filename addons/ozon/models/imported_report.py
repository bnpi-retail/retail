from odoo import models, fields, api

class ImportedReport(models.Model):
    _name = "ozon.imported_report"
    _description = "Импортированные отчеты Ozon"
    _order = "create_date desc"

    report_type = fields.Char(string="Тип", readonly=True)
    ad_campaign_identifier = fields.Char(string="Идентификатор рекламной кампании", readonly=True)
    start_date = fields.Date(string="Начало периода", readonly=True)
    end_date = fields.Date(string="Конец периода", readonly=True)
    