from odoo import models, fields, api


class Indicator(models.Model):
    _name = 'ozon.products.indicator'
    _description = 'Indicator'

    ozon_product_id = fields.Many2one('ozon.products')
    source = fields.Selection([('manager', 'Manager'), ('robot', 'Robot')])
    type = fields.Selection([
        ('not_concurrent_robot', 'Менее трех конкурентов(Робот)'),
        ('not_concurrent_manager', 'Менее трех конкурентов(Менеджер)'),
        ('cost_not_calculated', 'Себестоимость не подсчитана'),
    ])
    expiration_date = fields.Date()
    # next_check_date
    user_id = fields.Many2one('res.users')

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, f"{record.type} {record.user_id or ''}"))
        return res
