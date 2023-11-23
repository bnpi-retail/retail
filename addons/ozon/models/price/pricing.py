# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Pricing(models.Model):
    _name = 'ozon.pricing'
    _description = 'Ручное назначение цен'
        
    product = fields.Many2one('ozon.products', string='Лот')
    price = fields.Float(string='Цена лота, р.')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, f'{record.product}, {record.price} р.'))
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
        price_history = self.env['ozon.price_history']

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


                price_history.create({
                    'product': product.products.id,
                    'last_price': last_price,
                    'price': 0,
                    'custom_our_price': count_price_obj.price

                })
        return True
