from odoo import fields, models


class MassDataImport(models.Model):
    _name = "ozon.mass_data_import"
    _description = "Массовый импорт данных из стороннего сервиса"

    name = fields.Char()
    start_date = fields.Date()
    log_value = fields.Boolean()

