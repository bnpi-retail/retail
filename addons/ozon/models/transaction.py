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

    transaction_id = fields.Char(string="Идентификатор транзакции")
    transaction_date = fields.Date(string="Дата транзакции", readonly=True)
    order_date = fields.Date(
        string="Дата принятия отправления в обработку", readonly=True
    )
    name = fields.Char(string="Название транзакции", readonly=True)
    amount = fields.Float(
        string="Итого, р.",
        readonly=True,
    )
    skus = fields.Char(string="Список SKU товаров", readonly=True)
    products = fields.Many2many(
        "ozon.products",
        string="Лоты",
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
    promotion_expenses_ids = fields.One2many(
        "ozon.promotion_expenses",
        "transaction_id",
        string="Затраты на продвижение",
        readonly=True,
    )
