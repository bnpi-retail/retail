import datetime

from odoo import fields, models


class MassDataImport(models.Model):
    _name = "ozon.mass_data_import"
    _description = "Массовый импорт данных из стороннего сервиса"

    name = fields.Char()
    start_time = fields.Datetime(default=lambda x: datetime.datetime.now())
    finish_time = fields.Datetime()
    state = fields.Selection([('running', 'Running'), ('done', 'Done'), ('error', 'Error')], default='running')
    displaying_data = fields.Text()
    log_value = fields.Boolean(default=False)

