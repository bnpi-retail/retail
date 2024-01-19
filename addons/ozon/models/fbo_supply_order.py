# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OzonFboSupplyOrder(models.Model):
    _name = "ozon.fbo_supply_order"
    _description = "Завершённые заявки на поставку на склад Ozon (FBO)"

    created_at = fields.Date(string="Дата создания")
    supply_order_id = fields.Integer(string="Идентификатор")
    total_items_count = fields.Integer(string="Кол-во позиций товаров в заявке")
    total_quantity = fields.Integer(string="Кол-во единиц товаров в заявке")
    warehouse_id = fields.Many2one("ozon.warehouse", string="Склад поставки")
    fbo_supply_order_products_ids = fields.One2many(
        "ozon.fbo_supply_order_product",
        "fbo_supply_order_id",
        string="Товары в заявке",
    )


class OzonFboSupplyOrderProduct(models.Model):
    _name = "ozon.fbo_supply_order_product"
    _description = "Товар Ozon в заявке на поставку на склад Ozon (FBO)"

    fbo_supply_order_id = fields.Many2one(
        "ozon.fbo_supply_order", string="Заявка на поставку"
    )
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    qty = fields.Integer(string="Количество товара")
