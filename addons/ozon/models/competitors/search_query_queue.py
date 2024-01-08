from odoo import models, fields, api


class SearchQueryQueue(models.Model):
    _name = 'ozon.search_query_queue'
    _description = 'Очередь поисковых запросов'

    query = fields.Many2one('ozon.search_queries', string='Поисковый запрос')
    status = fields.Selection([
        ('complete', 'Выполнен'),
        ('in_processing', 'В обработке'),
        ('available', 'Доступен'),
    ], string='Статус', default='available')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            display_name = f"{record.query.words} - {record.status}"
            result.append((record.id, display_name))
        return result