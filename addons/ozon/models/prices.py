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
                logistics_ozon = self.env['ozon.logistics_ozon'] \
                    .search([], limit=1)
                
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

                # info.update({
                #     # Fix expensives
                #     'cost_price': self.create_cost_fix('Себестоимость', info['cost_price_product'], "Поиск себестоимости товара на последнюю дату" ),
                #     'cost_logistic': self.create_cost_fix(
                #             f'Логистика',
                #             logistics_ozon.price * localization_index.percent,
                #             'Себестоимость = Стоимость логистики * Индекс локализации'
                #         ),
                #     'cost_treatment': self.create_cost_fix('Стоимость обработки', 30, 'Фиксированное знаение'),
                # })

                price_history.create({
                    'product': product.products.id,
                    'provider': count_price_obj.provider.id,
                    'last_price': last_price,
                    'price': 0,
                    # 'fix_expensives': [
                    #     info['cost_price'],
                    #     info['cost_logistic'],
                    #     info['cost_treatment'],
                    # ],
                })
        return True


class FixExpenses(models.Model):
    _name = 'ozon.fix_expenses'
    _description = 'Фиксированные затраты'

    name = fields.Char(string='Наименование')
    price = fields.Float(string='Значение')
    discription = fields.Text(string='Описание')
    price_history_id = fields.Many2one('ozon.price_history', string='Товар')

class Costs(models.Model):
    _name = 'ozon.cost'
    _description = 'Процент от продаж'

    name = fields.Char(string='Наименование')
    price = fields.Float(string='Значение')
    discription = fields.Text(string='Описание')
    price_history_id = fields.Many2one('ozon.price_history', string='Товар')

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
            record.our_price = 2 * record.total_cost_fix


    @api.model
    def create(self, values):
        record = super(PriceHistory, self).create(values)
        
        record._compute_total_cost_fix()

        ### Нахождения себестоимости товара
        obj_cost_price = self.env['retail.cost_price'] \
            .search([('id', '=', record.product.products.id)],
                    order='timestamp desc',
                    limit=1)
        
        ### Создание объекта стоимости
        obj_fix__model_cost_price = self.env['ozon.fix_expenses'] \
            .create({'name': 'Себестоимость товара', 
                    'price': obj_cost_price.price,
                    'discription': "Поиск себестоимости товара в 'Retail'",
                    'price_history_id': record.id})

        ### Рассчет Стоимости логистики и создание объекта логистических затрат
        volume = record.product.products.volume
        obj_logistics_ozon = self.env['ozon.logistics_ozon'] \
            .search([('volume', '>=', volume),
                    ('trading_scheme', '=', record.product.trading_scheme)
                    ], order='volume', limit=1)
        
        localization_index = self.env['ozon.localization_index'] \
            .search([], limit=1)

        logistics_price = obj_logistics_ozon.price * localization_index.coefficient
        str_logistics_price = (f'Объем товара: {volume} '
                               f'Ближайшее значение в логистических затратах: {obj_logistics_ozon.price} '
                               f'Расчет = {obj_logistics_ozon.price} * {localization_index.coefficient} = {logistics_price}')

        obj_fix__model_logistics_price = self.env['ozon.fix_expenses'] \
            .create({'name': 'Стоимость логистики', 
                    'price': logistics_price,
                    'discription': str_logistics_price,
                    'price_history_id': record.id})

        ### Рассчет Стоимости обработки
        delivery_location = record.product.delivery_location
        obj_local_index = self.env['ozon.ozon_fee'] \
            .search([('delivery_location', '=', delivery_location)], limit=1)
        str_local_index = f"Ищем фиксированные затраты по 'Пункт приема товара' в комиссиях Ozon"

        obj_fix__model_local_index = self.env['ozon.fix_expenses'] \
            .create({'name': 'Фиксированные затраты', 
                    'price': obj_local_index.value,
                    'discription': str_local_index,
                    'price_history_id': record.id})
        
        ### Рассчет Комисиия Ozon
        obj_fee = self.env['ozon.ozon_fee'] \
            .search([('category.name_categories', '=', record.product.categories.name_categories)], limit=1)


        fee_price = obj_fee.value / 100 * obj_cost_price.price
        str_fee = f'{obj_fee.value} / 100 * {obj_cost_price.price}'
        type_comission = 'Процент' if obj_fee.type == 'percent' else 'Фиксированный'

        # if obj_fee.type == 'fix':
        #     fee_price = obj_fee.value
        #     str_fee = f'{obj_fee.value} * {record}'
        # elif obj_fee.type == 'percent':
        #     fee_price = obj_fee.value * obj_cost_price.price
        #     str_fee = f'{obj_fee.value} * {record}'

        obj_cost = self.env['ozon.cost'] \
            .create({'name': 'Комисиия Ozon', 
                    'price': fee_price,
                    'discription': (f'Тип: {type_comission}, '
                                    f'Комиссия: {obj_fee.value} '
                                    f'Значение комиссии: {str_fee} = {fee_price}'),
                    'price_history_id': record.id})
        
        record.write({'fix_expensives': [(4, obj_fix__model_cost_price.id),
                                         (4, obj_fix__model_logistics_price.id),
                                         (4, obj_fix__model_local_index.id)]})
        record.write({'costs': [(4, obj_cost.id)]})

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