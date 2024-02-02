# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions


class Seller(models.Model):
    _name = "retail.seller"
    _description = "Продавец"

    name = fields.Char(string="Название")
    ogrn = fields.Char(string="ОГРН")
    trade_name = fields.Char(string="Торговое название")
    is_my_shop = fields.Char(default=True)

    tax = fields.Selection(
        [
            ("earnings_minus_expenses_15", "Доходы минус расходы - 15%"),
            (
                "earnings_minus_expenses_20",
                "Доходы минус расходы - 20% (при превышении доходов)",
            ),
            ("earnings_6", "Доходы 6%"),
            ("earnings_8", "Доходы 8% (при превышении доходов)"),
        ],
        string="Налогообложение",
    )
    tax_percent = fields.Float(string="Процент налога", compute="_compute_tax_percent")
    tax_description = fields.Char(
        string="Описание налога", compute="_compute_tax_description"
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

    def _compute_tax_percent(self):
        for rec in self:
            if rec.tax == "earnings_minus_expenses_15":
                rec.tax_percent = 0.15
            elif rec.tax == "earnings_minus_expenses_20":
                rec.tax_percent = 0.2
            elif rec.tax == "earnings_6":
                rec.tax_percent = 0.06
            elif rec.tax == "earnings_8":
                rec.tax_percent = 0.08
            else:
                rec.tax_percent = 0

    def _compute_tax_description(self):
        for rec in self:
            rec.tax_description = dict(rec._fields["tax"].selection).get(rec.tax)
