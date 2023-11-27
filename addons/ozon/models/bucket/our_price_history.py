# -*- coding: utf-8 -*-

from email.policy import default
from odoo import models, fields, api


class OurFixExpenses(models.Model):
    _name = 'ozon.our_fix_expenses'
    _description = 'Фиксированные затраты наших цен'

    name = fields.Char(string='Наименование')
    price = fields.Float(string='Значение')
    discription = fields.Text(string='Описание')
    price_history_id = fields.Many2one('ozon.our_price_history', string='Товар')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, f'{record.name}, {record.price} р.'))
        return result
    

class OurCosts(models.Model):
    _name = 'ozon.our_cost'
    _description = 'Процент от продаж наших цен'

    name = fields.Char(string='Наименование')
    price = fields.Float(string='Значение')
    discription = fields.Text(string='Описание')
    price_history_id = fields.Many2one('ozon.our_price_history', string='Товар')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, f'{record.name}, {record.price} р.'))
        return result
        

class OurPriceHistory(models.Model):
    _name = 'ozon.our_price_history'
    _description = 'История наших цен'
    
    product = fields.Many2one('ozon.products', string="Товар")
    provider = fields.Many2one('retail.seller', string='Продавец')

    provider = fields.Many2one('retail.seller', string='Продавец')

    price = fields.Float(string='Цена конкурентов')
    competitors = fields.One2many('ozon.name_competitors', 'pricing_history_id', 
                                    string='Цены конкурентов',
                                    copy=True)
    
    last_price = fields.Float(string='Последняя цена', readonly=True)
    
    timestamp = fields.Date(string='Дата', 
                            default=fields.Date.today, readonly=True)

    fix_expensives = fields.One2many('ozon.our_fix_expenses', 'price_history_id',
                                     string=' Фиксированные затраты', 
                                     copy=True, readonly=True)
    
    total_cost_fix = fields.Float(string='Итого',
                            compute='_compute_total_cost_fix', store=True)

    costs = fields.One2many('ozon.our_cost', 'price_history_id', 
                            string='Процент от продаж',
                            copy=True, readonly=True)
    
    total_cost = fields.Float(string='Итого',
                            compute='_compute_total_cost', store=True)

    our_price = fields.Float(string='Расчетная цена',
                            compute='_compute_our_price', store=True)

    ideal_price = fields.Float(string='Идеальная цена',
                            compute='_compute_ideal_price', store=True)

    profit = fields.Float(string='Прибыль от расчетной цены',
                            compute='_compute_profit', store=True)

    custom_our_price = fields.Float(string='Своя расчетная цена', default=0)

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


    @api.depends('total_cost_fix')
    def _compute_ideal_price(self):
        for record in self:
            record.ideal_price = 2 * record.total_cost_fix


    @api.depends('ideal_price')
    def _compute_our_price(self):
        for record in self:
            if record.custom_our_price != 0:
                record.our_price = record.custom_our_price
            else:
                record.our_price = record.ideal_price


    @api.depends('our_price', 'total_cost_fix', 'total_cost')
    def _compute_profit(self):
        for record in self:
            total = record.our_price - record.total_cost_fix - record.total_cost
            record.profit = total


    @api.model
    def create(self, values):
        record = super(OurPriceHistory, self).create(values)
        
        record._compute_total_cost_fix()

        ### Нахождения себестоимости товара
        obj_cost_price = self.env['retail.cost_price'] \
            .search([('id', '=', record.product.products.id)],
                    order='timestamp desc',
                    limit=1)
        
        ### Создание объекта стоимости
        obj_fix__model_cost_price = self.env['ozon.our_fix_expenses'] \
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

        obj_fix__model_logistics_price = self.env['ozon.our_fix_expenses'] \
            .create({'name': 'Стоимость логистики', 
                    'price': logistics_price,
                    'discription': str_logistics_price,
                    'price_history_id': record.id})

        ### Рассчет Стоимости обработки
        delivery_location = record.product.delivery_location
        obj_local_index = self.env['ozon.ozon_fee'] \
            .search([('delivery_location', '=', delivery_location)], limit=1)
        str_local_index = f"Ищем фиксированные затраты по 'Пункт приема товара' в комиссиях Ozon"

        obj_fix__model_local_index = self.env['ozon.our_fix_expenses'] \
            .create({'name': 'Фиксированные затраты', 
                    'price': obj_local_index.value,
                    'discription': str_local_index,
                    'price_history_id': record.id})

        ### Создание записей о цене фиксированных затрат
        record.write({'fix_expensives': [(4, obj_fix__model_cost_price.id),
                                         (4, obj_fix__model_logistics_price.id),
                                         (4, obj_fix__model_local_index.id)]})

        ### Рассчет Комисиия Ozon
        obj_fee = self.env['ozon.ozon_fee'] \
            .search([('category.name_categories', '=', record.product.categories.name_categories)], limit=1)

        if obj_fee:
            fee_price = obj_fee.value / 100 * obj_cost_price.price
            str_fee = f'{obj_fee.value} / 100 * {obj_cost_price.price}'
            type_comission = 'Процент' if obj_fee.type == 'percent' else 'Фиксированный'

            # if obj_fee.type == 'fix':
            #     fee_price = obj_fee.value
            #     str_fee = f'{obj_fee.value} * {record}'
            # elif obj_fee.type == 'percent':
            #     fee_price = obj_fee.value * obj_cost_price.price
            #     str_fee = f'{obj_fee.value} * {record}'

            obj_cost = self.env['ozon.our_cost'] \
                .create({'name': 'Комисиия Ozon', 
                        'price': fee_price,
                        'discription': (f'Тип: {type_comission}, '
                                        f'Комиссия: {obj_fee.value} '
                                        f'Значение комиссии: {str_fee} = {fee_price}'),
                        'price_history_id': record.id})
            
            ### Создание записей о цене комиссии Ozon
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