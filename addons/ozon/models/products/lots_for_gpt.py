from odoo import models, fields, api


class LotsForGPT(models.Model):
    _name = 'ozon.lots_for_gpt'
    _description = 'Очередь для формирования поисковых запросов'

    product = fields.Many2one('ozon.products', string='Лот')
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
            result.append((record.id, record.product.products.name))
        return result
