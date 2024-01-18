# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Posting(models.Model):
    _name = "ozon.posting"
    _description = "Отправление Ozon"

    in_process_at = fields.Datetime(string="Дата и время начала обработки отправления")
    trading_scheme = fields.Selection(
        [("FBS", "FBS"), ("FBO", "FBO")], string="Схема торговли"
    )
    posting_number = fields.Char(string="Номер отправления")
    order_id = fields.Integer(
        string="Идентификатор заказа, к которому относится отправление"
    )
    status = fields.Char(string="Статус отправления")
    product_ids = fields.Many2many("ozon.products", string="Товары Ozon")
    region = fields.Char(string="Регион доставки")
    city = fields.Char(string="Город доставки")
    warehouse_id = fields.Many2one("ozon.warehouse", string="Склад Ozon")
    cluster_from = fields.Char(string="Код региона, откуда отправляется заказ")
    cluster_to = fields.Char(string="Код региона, куда отправляется заказ")
