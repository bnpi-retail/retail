# # -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions


class CountInsurancePercent(models.Model):
    _name = 'ozon.count_insurance_percent'
    _description = 'Вычисление процента по страхованию'

    timestamp = fields.Date(string='Дата расчета', 
                            default=fields.Date.today, readonly=True)
    start_date = fields.Date(string='Начальная дата расчета')
    end_date = fields.Date(string='Конечная дата расчета', 
                           default=fields.Date.today)
    product = fields.Many2one('ozon.products', string="Лот")
    value = fields.Float(string="Рассчитанный коэффициент", readonly=True)
    

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, f'{record.timestamp}, {record.product.products.name}, {record.start_date}-{record.start_date}, {record.value}'))
        return result


    def count_n_apply(self):
        movements_sell = self.env['ozon.movement_of_funds'].search([
            ('timestamp', '>=', self.start_date),
            ('timestamp', '<=', self.end_date),
            ('status', '=', 'positive'),
            ('product.id', '=', self.product.id),
        ])

        if len(movements_sell) == 0:
            raise exceptions.UserError("Нет данных о продаже товаров в указанном периоде времени.")

        movements_treatment = self.env['ozon.movement_of_funds'].search([
            ('timestamp', '>=', self.start_date),
            ('timestamp', '<=', self.end_date),
            ('status', '=', 'negative'),
            ('product.id', '=', self.product.id),
        ])

        if len(movements_treatment) == 0:
            raise exceptions.UserError("Нет данных о штрафах товаров в указанном периоде времени.")

        total_sell = sum(movements_sell.mapped('amount_of_money'))
        total_treatment = sum(movements_treatment.mapped('amount_of_money'))
        value = (total_treatment / total_sell) * 100

        self.env['ozon.count_insurance_percent'].create({
            'start_date': self.start_date,
            'end_date': self.end_date,
            'product': self.product.id,
            'value': value,
        })

        product_obj = self.env['ozon.products'].search([
            ('id', '=', self.product.id)
        ], limit=1)

        if not product_obj:
            raise exceptions.UserError("Лот не найден. Расчитанное значение не назначено.")
        product_obj.write({'insurance': value})

