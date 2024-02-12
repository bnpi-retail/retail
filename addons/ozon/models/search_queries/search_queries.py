from odoo import models, fields, api


class SearchQueries(models.Model):
    _name = 'ozon.search_queries'
    _description = 'Ключевые слова'

    words = fields.Char(string='Запрос')
    product_id = fields.Many2one('ozon.products', string='Продукт')
    issue_report_id = fields.Many2one('ozon.issue_report', 
                                      string='Отчет о выдаче')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, record.words))
        return result