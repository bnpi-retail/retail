from odoo import models, fields, api


class TrackedSearchQueries(models.Model):
    _name = 'ozon.tracked_search_queries'
    _description = 'Отслеживаемые поисковые запросы'

    name = fields.Char(string='Поисковый запрос')
    link_ozon_products = fields.Many2one('ozon.products', 
                                    string='Связанная запись в ozon.products')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result
