from datetime import datetime, time, timedelta
from odoo import models, fields, api


class ProductCompetitors(models.Model):
    _name = 'ozon.products_competitors'
    _description = 'Товары конкуренты'
    
    id_product = fields.Char(string='Id товара на Ozon')
    
    name = fields.Char(string='Наименование товара')

    url = fields.Char(string='URL товара', widget="url", 
                      help='Укажите ссылку на товар в поле')

    product = fields.Many2one('ozon.products', string='Лот')

    get_price_competitors_count = fields.Integer(compute='compute_count_price_competitors')
    @api.depends('product')
    def compute_count_price_competitors(self):
        for record in self:
            record.get_price_competitors_count = self.env['ozon.price_history_competitors'] \
                .search_count([('product_competitors', '=', record.id)])

    def get_price_competitors(self):
        self.ensure_one()

        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90) 

        return {
            'type': 'ir.actions.act_window',
            'name': 'История цен конкурентов',
            'view_mode': 'tree,graph',
            'res_model': 'ozon.price_history_competitors',
            'domain': [
                ('product_competitors', '=', self.id),
                ('timestamp', '>=', three_months_ago.strftime('%Y-%m-%d %H:%M:%S'))
            ],
            'context': {
                'create': False,
                'views': [(False, 'tree'), (False, 'form'), (False, 'graph')],
            }
        }

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result