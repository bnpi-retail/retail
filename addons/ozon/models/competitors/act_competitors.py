# -*- coding: utf-8 -*-

from odoo import models, fields, api


class NameCompetitors(models.Model):
    _name = 'ozon.name_competitors'
    _description = 'Наименования конкурентов'

    name = fields.Char(string='Название конкурента')
    price = fields.Float(string='Цена конкурента')
    act_competitors_id = fields.Many2one('ozon.act_competitors', string='Акт') 


class ActCompetitors(models.Model):
    _name = 'ozon.act_competitors'
    _description = 'Акт обоснования цены'

    timestamp = fields.Date(string='Дата', 
                            default=fields.Date.today,
                            readonly=True)
    
    product = fields.Many2one('ozon.products', string='Лот')

    competitors = fields.One2many('ozon.name_competitors', 'act_competitors_id', 
                                    string='Конкуренты',
                                    copy=True)

    price = fields.Float(string='Наша цена на основе цен конкурентов')


    @api.model
    def create(self, values):

        model_competitors = self.env['ozon.competitors']
        model_our_price_history = self.env['ozon.our_price_history']

        record = super(ActCompetitors, self).create(values)

        for competitor in record.competitors:
            model_competitors.create({
                'product': record.product.id,
                'name': competitor.name,
                'price': competitor.price,
            })

        model_our_price_history.create({
            'product': record.product.id,
            'price': record.price,
        })

        return record


    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id,
                           f'{record.timestamp},  '
                           f'{record.product.products.name}'))
        return result