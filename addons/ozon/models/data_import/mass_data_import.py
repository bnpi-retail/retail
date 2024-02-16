import datetime

from odoo import fields, models


class MassDataImport(models.Model):
    _name = "ozon.mass_data_import"
    _description = "Массовый импорт данных из стороннего сервиса"

    name = fields.Char()
    start_date = fields.Date(default=lambda: datetime.datetime.now())
    state = fields.Selection([('running', 'Running'), ('done', 'Done'), ('error', 'Error')])
    displaying_data = fields.Text()
    log_value = fields.Boolean(default=False)

