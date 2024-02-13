from odoo import models, fields, api


class SearchQueriesParser(models.Model):
    _name = 'ozon.search_queries_parser'
    _description = 'Поисковые запросы'

    search_query = fields.Char(string='Поисковый запрос')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, record.search_query))
        return result