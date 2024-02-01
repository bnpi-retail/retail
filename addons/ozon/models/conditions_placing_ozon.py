# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ConditionsPlacingOzon(models.Model):
    _name = "ozon.conditions_placing_ozon"
    _description = "Лот"

    name = fields.Char(string="Название")
    id_on_platform = fields.Char(string="ID на площадке")
    categorie = fields.Many2one("ozon.categories", string="Категория")

    products = fields.Many2one("retail.products", string="Лот")
    seller = fields.Many2one("retail.seller", string="Продавец")
    trading_scheme = fields.Selection(
        [
            ("FBS", "FBS"),
            ("FBO", "FBO"),
        ],
        string="Схема торговли",
    )
    delivery_location = fields.Selection(
        [
            ("ППЦ", "ППЦ/PC"),
            ("ПВЗ", "ПВЗ/PP"),
            ("СЦ", "СЦ/CS"),
        ],
        string="Пункт приема товара",
        help=(
            "ППЦ - Пункт приема заказов (Pickup Center), "
            "ПВЗ - Пункт выдачи заказов (Pickup Point), "
            "СЦ - Сервисный центр (Service Center)"
        ),
    )
