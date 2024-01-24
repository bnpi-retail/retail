import logging

from odoo import models, fields, api


class Indicator(models.Model):
    _name = 'ozon.products.indicator'
    _description = 'Indicator'

    active = fields.Boolean(default=True)
    name = fields.Char(size=100)
    ozon_product_id = fields.Many2one('ozon.products')
    source = fields.Selection([('manager', 'Manager'), ('robot', 'Robot')])
    type = fields.Selection([
        ('no_competitor_robot', 'Менее трех конкурентов(Робот)'),
        ('no_competitor_manager', 'Менее трех конкурентов(Менеджер)'),
        ('cost_not_calculated', 'Себестоимость не подсчитана'),
    ])
    expiration_date = fields.Date()
    # next_check_date
    user_id = fields.Many2one('res.users')

    # def name_get(self):
    #     res = []
    #     for record in self:
    #         res.append((record.id, f"{record.type} {record.user_id.name or ''}"))
    #     return res
