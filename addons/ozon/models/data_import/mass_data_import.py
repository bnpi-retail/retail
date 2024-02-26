import datetime
import logging

from odoo import fields, models, api


class MassDataImport(models.Model):
    _name = "ozon.mass_data_import"
    _description = "Массовый импорт данных из стороннего сервиса"

    name = fields.Char()
    start_time = fields.Datetime(default=lambda x: datetime.datetime.now())
    finish_time = fields.Datetime()
    state = fields.Selection([('running', 'Running'), ('done', 'Done'), ('error', 'Error')], default='running')
    log_value = fields.Boolean(default=False)
    expected_quantity = fields.Integer(string="Ожидаемое количество операций")
    executed_quantity = fields.Integer(string="Выполненное количество операций")

    ozon_mass_data_import_log_ids = fields.One2many("ozon.mass_data_import.log", "ozon_mass_data_import_id")

    @api.constrains('executed_quantity')
    def constraint_executed_quantity(self):
        if self.executed_quantity == self.expected_quantity:
            self.finish_time = datetime.datetime.now()
            self.state = 'done'


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


