# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CountPrice(models.Model):
    """
    Model for select products and count price
    """

    _name = 'ozon.count_price'
    _description = 'Акт расчета цен'
    
    product = fields.Many2many('ozon.products', string="Товар")
    provider = fields.Many2one('retail.seller', string='Продавец')


    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            seller = record.provider.name
            if not seller:
                seller = 'Отсутствует'
            result.append((record.id, f'Продавец: {seller}, Позиций: {len(record.product)}'))
        return result
    

    def create_fix_cost(self, name: str, price: float) -> int:
        """
        Create record in 'ozon.fix_expenses' model
        """
        cost_price = self.env['ozon.fix_expenses']
        return cost_price.create({
            'name': name, 
            'price': price,
        }).id
    
    def create_cost_for_history(self, name: str, price: float) -> int:
        """
        Create record in 'ozon.cost' model
        """
        cost_price = self.env['ozon.cost']
        return cost_price.create({
            'name': name, 
            'price': price,
        }).id

    def select_cost_price(self, product) -> int:
        """
        Select cost price of product
        """
        cost_price = self.env['retail.cost_price'].search(
            [
                ('id', '=', product.products.id),
                ('seller.id', '=', product.seller.id)
            ]
            , limit=1,
            order='timestamp desc'
        ).price
        return cost_price


    def count_price(self, product) -> int:
        """
        Count price of product
        """
        return 0
    

    def apply_product(self) -> bool:
        """
        Function for count price
        """
        price_history = self.env['ozon.price_history']

        for count_price_obj in self:
            for product in count_price_obj.product:
                
                last_price = self.env['ozon.price_history'] \
                    .search([('product', '=', product.products.id),], limit=1,).price
                localization_index = self.env['ozon.localization_index'] \
                    .search([], limit=1)
                ozon_fee = self.env['ozon.ozon_fee'] \
                    .search([], limit=1)
                logistics_ozon = self.env['ozon.logistics_ozon'] \
                    .search([], limit=1)
                
                product_info = product.products
                
                info = {
                    # Info in all linked models

                    # Info in linked model 'retail.cost_price'
                    'cost_price': self.select_cost_price(product),

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

                total_expensive = info['cost_price'] + logistics_ozon.price + 0
                ozon_fee_price = ozon_fee.value * (total_expensive + total_expensive + info['cost_price'])

                info.update({
                    # Fix expensives
                    'cost_price': self.create_fix_cost('Себестоимость', info['cost_price']),
                    'cost_logistic': self.create_fix_cost(
                            f'Логистика {logistics_ozon.price} * {localization_index.percent}',
                            logistics_ozon.price * localization_index.percent
                        ),
                    'cost_treatment': self.create_fix_cost('Стоимость обработки', 30),

                    # Another expensives
                    'total_expensive_record': self.create_cost_for_history('Итого затраты', total_expensive),
                    'ideal_margin': self.create_cost_for_history('Идеальная маржа', total_expensive),
                    'ideal_price': self.create_cost_for_history('Идеальная цена', total_expensive + total_expensive),
                    'our_price': self.create_cost_for_history('Наша цена', total_expensive + total_expensive + info['cost_price']),
                    'fee_ozon': self.create_cost_for_history(f'Комиссия Ozon ({ozon_fee.type})', ozon_fee_price),
                    'all_expensive': self.create_cost_for_history('Все затраты', total_expensive + ozon_fee_price),
                    'profit': self.create_cost_for_history('Прибыль', 156),

                    # Calculated data
                    'price': self.count_price(product),
                    'total_expensive': info['cost_price'] + logistics_ozon.price + 0,
                })

                price_history.create({
                    'price': info['price'],
                    'product': product.products.id,
                    'provider': count_price_obj.provider,
                    'last_price': last_price,
                    'price': 156,
                    'costs': [
                        info['total_expensive_record'],
                        info['ideal_margin'],
                        info['ideal_price'],
                        info['our_price'],
                        info['fee_ozon'],
                        info['all_expensive'],
                        info['profit'],
                    ],
                    'fix_expensives': [
                        info['cost_price'],
                        info['cost_logistic'],
                        info['cost_treatment'],
                    ],
                })
        return True


class FixExpenses(models.Model):
    _name = 'ozon.fix_expenses'
    _description = 'Фиксированные затраты'

    name = fields.Char(string='Наименование')
    price = fields.Float(string='Значение', default=0)
    price_history_id = fields.Many2one(
        'ozon.price_history', string='ID истории цены'
    )

class Costs(models.Model):
    _name = 'ozon.cost'
    _description = 'Затраты/Приходы'

    name = fields.Char(string='Наименование')
    price = fields.Float(string='Значение', default=0)
    price_history_id = fields.Many2one(
        'ozon.price_history', string='ID истории цены'
    )

class PriceHistory(models.Model):
    _name = 'ozon.price_history'
    _description = 'История цен'
    
    product = fields.Many2one('ozon.products', string="Лот")
    provider = fields.Char(string='Поставщик')
    price = fields  .Float(string='Цена')
    last_price = fields.Float(string='Последняя цена', readonly=True)
    timestamp = fields.Date(
        string='Дата', default=fields.Date.today, readonly=True
    )
    
    costs = fields.One2many(
        'ozon.cost', 'price_history_id', string='Затраты/Приходы', 
        copy=True
    )

    fix_expensives = fields.One2many(
        'ozon.fix_expenses', 'price_history_id', string='Затраты/Приходы', 
        copy=True
    )