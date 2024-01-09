# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CostPrice(models.Model):
    _name = "retail.cost_price"
    _description = "Себестоимость"

    timestamp = fields.Date(string="Дата", default=fields.Date.today, readonly=True)
    product_id = fields.Many2one("retail.products", string="Товар")
    cost_type_id = fields.Many2one("retail.cost_act_type", string="Тип")
    price = fields.Float(string="Стоимость")

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.product_id.name))
        return result
