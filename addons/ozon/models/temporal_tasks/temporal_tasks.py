import uuid

from odoo import models, fields, api


class TemporalTasks(models.Model):
    _name = 'ozon.temporal_tasks'
    _description = 'Задачи по времени в Temporal'

    description = fields.Char(string='Описание задачи')
    numbers_products_in_query = fields.Integer(string='Количество объектов за раз')
    numbers_workers = fields.Integer(string='Количество обработчиков')
    unique_id = fields.Char(string='Уникальный индетификатор задачи', readonly=True)


class TemporalTasksCreate(models.Model):
    _inherit = "ozon.temporal_tasks"

    @api.model
    def create(self, values):
        record = super(TemporalTasks, self).create(values)
        record.unique_id = str(uuid.uuid4())
        return record


class TemporalTasksNameGet(models.Model):
    _inherit = "ozon.temporal_tasks"

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, record.description))
        return result