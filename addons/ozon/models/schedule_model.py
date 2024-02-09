from odoo import models, fields


class Schedule(models.Model):
    _name = "ozon.schedule"
    _description = 'schedule'

    ozon_products_checking_last_time = fields.Datetime()
