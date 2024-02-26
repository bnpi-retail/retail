import datetime

from odoo import fields, models


class MassDataImport(models.Model):
    _name = "ozon.mass_data_import"
    _description = "Массовый импорт данных из стороннего сервиса"

    name = fields.Char()
    start_time = fields.Datetime(default=lambda x: datetime.datetime.now())
    finish_time = fields.Datetime()
    state = fields.Selection([('running', 'Running'), ('done', 'Done'), ('error', 'Error')], default='running')
    log_value = fields.Boolean(default=False)

    ozon_mass_data_import_log_ids = fields.One2many("ozon.mass_data_import.log", "ozon_mass_data_import_id")


class MassDataImportLog(models.Model):
    _name = "ozon.mass_data_import.log"
    _description = "Лог по активитис"

    name = fields.Char()
    start_time = fields.Datetime(default=lambda x: datetime.datetime.now())
    finish_time = fields.Datetime()
    state = fields.Selection([('running', 'Running'), ('done', 'Done'), ('error', 'Error')], default='running')
    displaying_data = fields.Text()
    log_value = fields.Boolean(default=False)

    ozon_mass_data_import_id = fields.Many2one("ozon.mass_data_import")


