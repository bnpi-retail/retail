from odoo import models, fields, api


class ProductSale(models.Model):
    _name = "ozon.sale"
    _description = "Продажи товаров"
    _order = "date desc"

    transaction_identifier = fields.Char(string="Идентификатор транзакции", readonly=True)
    product = fields.Many2one("ozon.products", string="Товар Ozon", readonly=True)
    product_id_on_platform = fields.Char(string="Product ID", readonly=True)
    date = fields.Date(string="Дата продажи", readonly=True)
    qty = fields.Integer(string="Кол-во проданного товара", readonly=True)
    revenue = fields.Float(string="Выручка", readonly=True)
    sale_commission = fields.Float(string="Комиссия за продажу", readonly=True)
    services_cost = fields.Float(string="Общая стоимость доп.услуг", readonly=True)
    profit = fields.Float(string="Итого (цена продажи - комиссия - доп.услуги)", readonly=True)
    is_calculate = fields.Boolean(string="Учавствует в расчетах", default=False)