# -*- coding: utf-8 -*-

from odoo import models, fields, api


class NameCharacteristic(models.Model):
    _name = 'ozon.name_info'
    _description = 'Наименование характеристики карточки'

    name = fields.Char(string='Наименование')

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, f'{record.name}'))
        return result


class AdditionalInfo(models.Model):
    _name = 'ozon.issue_report_products_info'
    _description = 'Характеристики карточки'

    name = fields.Many2one('ozon.name_info', string='Наименование')
    rating = fields.Integer(string='Рейтинг')
    product_reference = fields.Many2one('ozon.issue_report_products', string='Продукт отчета о выдаче')


    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, f'{record.name.name}, {record.rating}'))
        return result



class IssueReportProducts(models.Model):
    _name = 'ozon.issue_report_products'
    _description = 'Продукты отчета о выдаче'

    number = fields.Integer(string='Номер')
    product = fields.Reference(
        selection=[
            ('ozon.products', 'Лот'),
            ('ozon.products_competitors', 'Продукт конкурента')
        ],
        string='Товар',
    )
    additional_info_ids = fields.One2many('ozon.issue_report_products_info', 'product_reference', string='Характеристики товара')
    issue_report_id = fields.Many2one('ozon.issue_report', string='Отчет о выдаче')

    @api.model
    def create(self, vals):
        if 'issue_report_id' in vals:
            issue_report_id = vals['issue_report_id']
            related_products = self.env['ozon.issue_report_products'].search_count([('issue_report_id', '=', issue_report_id)])
            vals['number'] = related_products + 1
        return super(IssueReportProducts, self).create(vals)

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, f'{record.number}, {record.product}'))
        return result


class IssueReport(models.Model):
    _name = 'ozon.issue_report'
    _description = 'Отчет о выдаче'

    timestamp = fields.Date(string='Дата импорта', 
                            default=fields.Date.today,
                            readonly=True)
    search_queries = fields.Many2one('ozon.search_queries', string='Запрос')

    products = fields.One2many('ozon.issue_report_products',
                               'issue_report_id',
                               string='Товары')

    def name_get(self):
        result = []
        for record in self:
            if record.search_queries:
                result.append((record.id, f'{record.timestamp}, {record.search_queries.words}'))
            else:
                result.append((record.id, record.timestamp))
        return result
