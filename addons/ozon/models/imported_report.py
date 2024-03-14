from odoo import models, fields, api

class ImportedReport(models.Model):
    _name = "ozon.imported_report"
    _description = "Импортированные отчеты Ozon"
    _order = "create_date desc"

    report_type = fields.Char(string="Тип", readonly=True)
    ad_campaign_identifier = fields.Char(string="Идентификатор рекламной кампании", readonly=True)
    start_date = fields.Date(string="Начало периода", readonly=True)
    end_date = fields.Date(string="Конец периода", readonly=True)
    
    def get_report(self, data):
        ad_campaign_identifier = data.get("ad_campaign_identifier")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        report = self.search([
            ("ad_campaign_identifier", "=", ad_campaign_identifier),
            ("start_date", ">=", start_date),
            ("start_date", "<=", end_date),
        ])
        return report if report else None

    def name_get(self):
        result = []
        for r in self:
            result.append(
                (r.id, f"{r.report_type} №{r.ad_campaign_identifier} "
                 f"за период: {r.start_date} - {r.end_date}")
            )
        return result