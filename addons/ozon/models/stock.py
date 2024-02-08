from email.policy import default
from odoo import models, fields, api


class ProductStock(models.Model):
    _name = "ozon.stock"
    _description = "Остатки товаров"

    product = fields.Many2one("ozon.products", string="Товар Ozon")
    id_on_platform = fields.Char(string="Product ID", readonly=True)
    timestamp = fields.Date(string="Дата", default=fields.Date.today)
    stocks_fbs = fields.Integer(string="Остатки FBS")
    stocks_reserved_fbs = fields.Integer(string="Зарезервировано остатков FBS")
    stocks_fbo = fields.Integer(string="Остатки FBO")
    fbs_warehouse_product_stock_ids = fields.One2many(
        "ozon.fbs_warehouse_product_stock",
        "stock_id",
        string="Остатки товара на складе FBS",
    )

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            id = record.id
            result.append(
                (id, f"{record.timestamp},  " f"{record.product.products.name}")
            )
        return result


class FbsWarehouseProductStock(models.Model):
    _name = "ozon.fbs_warehouse_product_stock"
    _description = "Остатки товара на складе FBS"

    timestamp = fields.Date(string="Дата", default=fields.Date.today)
    stock_id = fields.Many2one("ozon.stock", string="Общие остатки товара")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    warehouse_id = fields.Many2one("ozon.warehouse", string="Склад Ozon")
    qty = fields.Integer(string="Кол-во товара на складе")
