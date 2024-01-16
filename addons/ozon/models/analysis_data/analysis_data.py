# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AnalysisData(models.Model):
    _name = "ozon.analysis_data"
    _description = "Аналитические данные"

    product = fields.Many2one("ozon.products", string="Товар Ozon")
    timestamp = fields.Date(string="Дата", default=fields.Date.today)
    hits_view = fields.Integer(string="Всего показов")
    hits_tocart = fields.Integer(string="Всего добавлено в корзину")

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            id = record.id
            if record.product.products.name:
                name = (id, f"{record.timestamp},  " f"{record.product.products.name}")
            else:
                name = (id, f"{record.timestamp}")
            result.append(name)
        return result