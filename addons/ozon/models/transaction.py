# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OzonServices(models.Model):
    _name = "ozon.ozon_services"
    _description = "Дополнительные услуги Озон"

    name = fields.Char(string="Название услуги", readonly=True)
    price = fields.Float(string="Стоимость услуги", readonly=True)


class Transactions(models.Model):
    _name = "ozon.transaction"
    _description = "Транзакции"
    _order = "transaction_date desc"

    transaction_id = fields.Char(string="Идентификатор транзакции")
    transaction_date = fields.Date(string="Дата транзакции", readonly=True)
    order_date = fields.Date(
        string="Дата принятия отправления в обработку", readonly=True
    )
    name = fields.Char(string="Название транзакции", readonly=True)
    transaction_type = fields.Char(string="Тип транзакции", readonly=True)
    accruals_for_sale = fields.Float(string="Стоимость товаров с учётом скидок продавца", readonly=True)
    sale_commission = fields.Float(string="Комиссия за продажу или возврат комиссии за продажу", 
                                   readonly=True)
    amount = fields.Float(string="Итоговая сумма операции (стоимость - комиссия - стоимость доп.услуг)", 
                          readonly=True)
    skus = fields.Char(string="Список SKU товаров", readonly=True)
    products = fields.Many2many(
        "ozon.products",
        string="Товары",
        copy=True,
        readonly=True,
    )
    services = fields.Many2many(
        "ozon.ozon_services",
        string="Дополнительные услуги Ozon",
        copy=True,
        readonly=True,
    )
    posting_number = fields.Char(
        string="Номер отправления",
        readonly=True,
    )
