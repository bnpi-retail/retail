# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OzonServices(models.Model):
    _name = "ozon.ozon_services"
    _description = "Дополнительные услуги Озон"

    name = fields.Char(string="Название услуги", readonly=True)
    price = fields.Float(string="Стоимость услуги", readonly=True)

    transaction_id = fields.Many2one("ozon.transaction", string="Транзакция")


class Transactions(models.Model):
    _name = "ozon.transaction"
    _description = "Транзакции"

    date = fields.Date(string="Дата транзакции", readonly=True)
    name = fields.Char(string="Название транзакции", readonly=True)
    status = fields.Selection(
        [
            ("positive", "Приход"),
            ("negative", "Расход"),
        ],
        string="Тип учета",
    )
    category = fields.Selection(
        [
            ("sale", "Продажа"),
            ("processing", "Обработка"),
            ("insurance", "Страховка"),
        ],
        string="Категория",
    )
    amount = fields.Float(string="Общая сумма, р.")
    product = fields.One2many(
        "ozon.products",
        "transaction_id",
        string="Лоты",
        copy=True,
        readonly=True,
    )
    services = fields.One2many(
        "ozon.ozon_services",
        "transaction_id",
        string="Дополнительные услуги Ozon",
        copy=True,
        readonly=True,
    )

    # def name_get(self):
    #     """
    #     Rename name records
    #     """
    #     result = []
    #     for record in self:
    #         result.append(
    #             (
    #                 record.id,
    #                 f"{record.timestamp}, {record.categorie}, {record.product.products.name}",
    #             )
    #         )
    #     return result
