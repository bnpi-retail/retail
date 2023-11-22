# # -*- coding: utf-8 -*-

from odoo import models, fields, api


class Categories(models.Model):
    _name = 'ozon.categories'
    _description = 'Категории Ozon'

    name_categories = fields.Char(string='Название категории')
    # name_fee = fields.Char(string='Наименование комиссии')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, record.name_categories))
        return result
    

    # @api.model
    # def create(self, values):
    #     if 'name_categories' in values and 'example' in values['name_categories']:
    #         values['name_fee'] = 'Modified Example'

    #     new_record = super(Categories, self).create(values)

    #     return new_record