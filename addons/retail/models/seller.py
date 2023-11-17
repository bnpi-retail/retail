# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions


class Seller(models.Model):
    _name = 'retail.seller'
    _description = 'Cost on platform'

    name = fields.Char(string='Имя продовца')
    ogrn = fields.Char(string='ОГРН', unique=True)
    fee = fields.Float(string='Налогообложение, %')

    @api.model
    def create(self, values):
        if 'ogrn' in values:
            ogrn = values['ogrn']
            if not ogrn.isdigit():
                raise exceptions.ValidationError('ОГРН должен быть 13-значным числом')
        
        return super(Seller, self).create(values)
