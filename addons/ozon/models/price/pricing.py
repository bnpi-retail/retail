# -*- coding: utf-8 -*-

from odoo import models, fields, api


class NameCompetitors(models.Model):
    _name = 'ozon.name_competitors'
    _description = 'Наименования конкурентов'

    name = fields.Char(string='Название конкурента')
    price = fields.Float(string='Цена конкурента')
    pricing_id = fields.Many2one('ozon.pricing',
                                 string='Акт ручного назначения цен')
    pricing_history_id = fields.Many2one('ozon.our_price_history',
                                 string='Акт ручного назначения цен')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, f'{record.name}, {record.price} р.'))
        return result
    

class Pricing(models.Model):
    _name = 'ozon.pricing'
    _description = 'Ручное назначение цен'
        
    product = fields.Many2one('ozon.products', string='Лот')
    
    price = fields.Float(string='Цена лота, р.')

    competitors = fields.One2many('ozon.name_competitors', 'pricing_id', 
                                    string='Конкуренты',
                                    copy=True)
    

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, f'{record.product.products.name}, {record.price} р.'))
        return result
    

    def select_cost_price(self, product) -> int:
        """
        Select cost price of product
        """
        cost_price = self.env['retail.cost_price'] \
            .search([('id', '=', product.products.id),
                     ('seller.id', '=', product.seller.id)],
                     limit=1, order='timestamp desc').price
        return cost_price



    def apply(self) -> bool:
        """
        Function for count price
        """
        price_history = self.env['ozon.our_price_history']

        for count_price_obj in self:
            for product in count_price_obj.product:
                
                last_price = self.env['ozon.price_history'] \
                    .search([('product', '=', product.products.id),], limit=1,).price
                
                product_info = product.products
                
                info = {
                    'cost_price_product': self.select_cost_price(product),

                    # Info in linked model 'product'
                    'name': product_info.name,
                    'description': product_info.description,
                    'product_id': product_info.product_id,
                    'length': product_info.length,
                    'width': product_info.width,
                    'height': product_info.height,
                    'weight': product_info.weight,
                    'volume': product_info.volume,

                    # Info in self model
                    'categories': product.categories,
                    'id_on_platform': product.id_on_platform,
                    'full_categories': product.full_categories,
                    'products': product.products,
                    'index_localization': product.index_localization,
                    'trading_scheme': product.trading_scheme,
                    'delivery_location': product.delivery_location,
                }

            all_competitor = []
            for competitor in count_price_obj.competitors:
                self.env['ozon.price_history_competitors'].create({
                    'name': competitor.name,
                    'price': competitor.price,
                    'product': count_price_obj.product.id,
                })
                all_competitor.append((4, competitor.id))

            price_history.create({
                'product': product.products.id,
                'last_price': last_price,
                'competitors': all_competitor,
                'custom_our_price': count_price_obj.price,
            })

        return True
