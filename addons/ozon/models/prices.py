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
    

    def create_cost_fix(self, name: str, price: float, discription: str) -> int:
        """
        Create record in 'ozon.fix_expenses' model
        """
        cost_price = self.env['ozon.fix_expenses']
        return cost_price.create({
            'name': name, 
            'price': price,
            'discription': discription,
        }).id
    
    def create_cost(self, name: str, price: float, discription: str) -> int:
        """
        Create record in 'ozon.cost' model
        """
        cost_price = self.env['ozon.cost']
        return cost_price.create({
            'name': name, 
            'price': price,
            'discription': discription,
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


                info.update({
                    # Fix expensives
                    'cost_price': self.create_cost_fix('Себестоимость', info['cost_price'], "Поиск себестоимости товара на последнюю дату" ),
                    'cost_logistic': self.create_cost_fix(
                            f'Логистика',
                            logistics_ozon.price * localization_index.percent,
                            'Себестоимость = Стоимость логистики * Индекс локализации'
                        ),
                    'cost_treatment': self.create_cost_fix('Стоимость обработки', 30, 'Фиксированное знаение'),

                    # Another expensives
                    # 'total_expensive_record': self.create_cost('Итого затраты', total_expensive),
                    # 'ideal_margin': self.create_cost('Идеальная маржа', product.fix, 'Процент от себестоимости 20%'),
                    # 'ideal_price': self.create_cost('Идеальная цена', total_expensive + total_expensive),
                    # 'our_price': self.create_cost('Наша цена', total_expensive + total_expensive + info['cost_price']),
                    # 'fee_ozon': self.create_cost(f'Комиссия Ozon', ozon_fee_price, 'Комиссия от актуальной цены'),
                    # 'all_expensive': self.create_cost('Все затраты', total_expensive + ozon_fee_price),
                    'profit': self.create_cost('Прибыль', 156, 'Прибыль = Комиссия Ozon + Идеальная маража + Фиксированные затраты'),

                    # Calculated data
                    'price': self.count_price(product),
                    'total_expensive': info['cost_price'] + logistics_ozon.price + 0,
                })

                price_history.create({
                    'price': info['price'],
                    'product': product.products.id,
                    'provider': count_price_obj.provider.id,
                    'last_price': last_price,
                    'price': 156,
                    'costs': [
                        # info['total_expensive_record'],
                        # info['ideal_margin'],
                        # info['ideal_price'],
                        # info['our_price'],
                        # info['fee_ozon'],
                        # info['all_expensive'],
                        # info['profit'],
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
    price = fields.Float(string='Значение')
    discription = fields.Text(string='Описание')
    price_history_id = fields.Many2one('ozon.price_history', string='Лот')

class Costs(models.Model):
    _name = 'ozon.cost'
    _description = 'Процент от продаж'

    name = fields.Char(string='Наименование')
    price = fields.Float(string='Значение')
    discription = fields.Text(string='Описание')
    price_history_id = fields.Many2one('ozon.price_history', string='Лот')

class PriceHistory(models.Model):
    _name = 'ozon.price_history'
    _description = 'История цен'
    
    product = fields.Many2one('ozon.products', string="Товар")
    provider = fields.Many2one('retail.seller', string='Продавец')
    price = fields.Float(string='Цена конкурентов')
    last_price = fields.Float(string='Последняя цена', readonly=True)
    
    timestamp = fields.Date(string='Дата', 
                            default=fields.Date.today, readonly=True)

    fix_expensives = fields.One2many('ozon.fix_expenses', 'price_history_id',
                                     string=' Фиксированные затраты', 
                                     copy=True, readonly=True)
    
    total_cost_fix = fields.Float(string='Итого',
                            compute='_compute_total_cost_fix', store=True)

    costs = fields.One2many('ozon.cost', 'price_history_id', 
                            string='Процент от продаж',
                            copy=True, readonly=True)
    
    total_cost = fields.Float(string='Итого',
                            compute='_compute_total_cost', store=True)

    our_price = fields.Float(string='Расчетная цена',
                            compute='_compute_our_price', store=True)

    ideal_price = fields.Float(string='Идеальная цена',
                            compute='_compute_our_price', store=True)
    
    profit = fields.Float(string='Прибыль от расчетной цены')

    @api.depends('costs.price')
    def _compute_total_cost(self):
        for record in self:
            total = sum(record.costs.mapped('price'))
            record.total_cost = total


    @api.depends('fix_expensives.price')
    def _compute_total_cost_fix(self):
        for record in self:
            total = sum(record.fix_expensives.mapped('price'))
            record.total_cost_fix = total


    @api.depends('fix_expensives.price', 'costs.price')
    def _compute_our_price(self):
        for record in self:
            record.our_price = record.total_cost + record.total_cost_fix


    @api.depends('fix_expensives.price')
    def _compute_our_price(self):
        for record in self:
            record.ideal_price = 2 * record.total_cost_fix


    @api.model
    def create(self, values):
        record = super(PriceHistory, self).create(values)

        record._compute_total_cost_fix()

        model_cost_price = self.env['ozon.cost']
        obj_cost_price = model_cost_price.create({
            'name': 'Идеальная маржа', 
            'price': 0.2 * record.total_cost_fix,
            'discription': '20% процентов от фикс. затрат.',
            'price_history_id': record.id,
        })
        record.write({'costs': [(4, obj_cost_price.id)]})

        return record
    

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            id = record.id
            result.append((id,
                           f'{record.timestamp},  '
                           f'{record.product.products.name}'))
        return result