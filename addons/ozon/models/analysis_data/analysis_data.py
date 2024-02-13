# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AnalysisData(models.Model):
    _name = "ozon.analysis_data"
    _description = "Данные интереса к продуктам"

    timestamp_from = fields.Date(string="Начало периода", readonly=True)
    timestamp_to = fields.Date(string="Конец периода", readonly=True)

    product = fields.Many2one("ozon.products", string="Товар Ozon")
    hits_view = fields.Integer(string="Всего показов")
    hits_tocart = fields.Integer(string="Всего добавлено в корзину")

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            id = record.id
            name = (id, f"{record.product.products.name}")
            result.append(name)
        return result
