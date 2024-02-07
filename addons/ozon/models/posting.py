# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Posting(models.Model):
    _name = "ozon.posting"
    _description = "Отправление Ozon"
    _order = "in_process_at desc"

    posting_number = fields.Char(string="Номер отправления", index=True)
    in_process_at = fields.Date(string="Дата начала обработки отправления")
    trading_scheme = fields.Selection(
        [("FBS", "FBS"), ("FBO", "FBO")], string="Схема торговли"
    )
    order_id = fields.Char(
        string="Идентификатор заказа, к которому относится отправление"
    )
    status = fields.Selection(
        [("delivered", "Доставлено"), ("cancelled", "Отменено")], string="Статус"
    )
    product_ids = fields.Many2many("ozon.products", string="Товары Ozon")
    skus = fields.Char(string="Список SKU товаров", readonly=True)
    region = fields.Char(string="Регион доставки")
    city = fields.Char(string="Город доставки")
    warehouse_id = fields.Many2one("ozon.warehouse", string="Склад Ozon")
    cluster_from = fields.Char(string="Код региона, откуда отправляется заказ")
    cluster_to = fields.Char(string="Код региона, куда отправляется заказ")
    promotion_expenses_id = fields.Many2one(
        "ozon.promotion_expenses",
        string="Затраты на продвижение",
        readonly=True,
    )
