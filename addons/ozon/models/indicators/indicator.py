from odoo import models, fields


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
    end_date = fields.Date()
    expiration_date = fields.Date()
    # next_check_date
    user_id = fields.Many2one('res.users')

