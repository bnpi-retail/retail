# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Product(models.Model):
    _name = "ozon.products"
    _description = "Лоты"

    categories = fields.Many2one("ozon.categories", string="Название категории")
    id_on_platform = fields.Char(string="ID на площадке")
    full_categories = fields.Char(string="Наименоваие раздела")
    products = fields.Many2one("retail.products", string="Товар")
    seller = fields.Many2one("retail.seller", string="Продавец")
    index_localization = fields.Many2one(
        "ozon.localization_index", string="Индекс локализации"
    )
    insurance = fields.Float(string="Страховой коэффициент, %")
    search_queries = fields.One2many(
        "ozon.search_queries", "product_id", string="Поисковые запросы"
    )
    trading_scheme = fields.Selection(
        [("FBS", "FBS"), ("FBO", "FBO"), ("-", "-")], string="Схема торговли"
    )

    delivery_location = fields.Selection(
        [
            ("PC", "ППЗ/PC"),
            ("PP", "ПВЗ/PP"),
            ("SC", "СЦ/SC"),
            ("TSC", "ТСЦ/TSC"),
            ("-", "-"),
        ],
        string="Пункт приема товара",
        help=(
            "ППЦ - Пункт приема заказов (Pickup Center), "
            "ПВЗ - Пункт выдачи заказов (Pickup Point), "
            "СЦ - Сервисный центр (Service Center)"
        ),
    )

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.products.name))
        return result
