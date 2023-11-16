# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LocalizationIndex(models.Model):
    _name = 'retail.localization_index'
    _description = 'Индекс локализации'

    lower_threshold = fields.Float(string='Нижний порог')
    upper_threshold = fields.Float(string='Верхний порог')
    coefficient = fields.Float(string='Коэффициент')
    percent = fields.Float(string='Процент')

    @api.constrains('lower_threshold')
    def _check_lower_threshold(self):
        for record in self:
            if record.lower_threshold < 0:
                raise ValidationError("Нижний порог не может быть меньше 0.")

    @api.constrains('upper_threshold')
    def _upper_threshold(self):
        for record in self:
            if record.upper_threshold > 100:
                raise ValidationError("Верхний порог не может быть больше 100.")
            
    @api.constrains('coefficient')
    def _coefficient(self):
        for record in self:
            if record.coefficient < 0 or record.coefficient > 1:
                raise ValidationError("Коэффициент может принимать значения от 0 до 1.")

    @api.constrains('percent')
    def _percent(self):
        for record in self:
            if record.percent < 0 or record.percent > 100:
                raise ValidationError("Коэффициент может принимать значения от 0 до 100.")