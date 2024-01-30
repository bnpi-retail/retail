# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions


class Seller(models.Model):
    _name = "retail.seller"
    _description = "Продавец"

    name = fields.Char(string="Название")
    ogrn = fields.Char(string="ОГРН")

    tax = fields.Selection(
        [
            ("earnings_minus_expenses_15", "Доходы минус расходы - 15%"),
            ("earnings_6", "Доходы 6%"),
        ],
        string="Налогообложение",
    )

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result

    @api.model
    def create(self, values):
        # if 'ogrn' in values:
        #     ogrn = values['ogrn']
        #     if not ogrn.isdigit():
        # raise exceptions.ValidationError('ОГРН должен быть 13-значным числом')

        return super(Seller, self).create(values)
