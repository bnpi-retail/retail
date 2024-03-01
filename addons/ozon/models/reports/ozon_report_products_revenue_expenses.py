from odoo import models, fields


class OzonReportProductsRevenueExpenses(models.Model):
    _name = "ozon.report.products_revenue_expenses"
    _description = "Строки отчета по выручке и расходах продукта за период внутри продукта"

    identifier = fields.Integer(string="Идентификатор")
    ozon_products_id = fields.Many2one("ozon.products", string="Товар Ozon")
    name = fields.Char(string="Название")
    comment = fields.Text(string="Комментарий", readonly=True)
    value = fields.Float(string="Значение для товара")
    qty = fields.Integer(string="Количество")
    percent = fields.Float(string="Процент от выручки товара")
    percent_from_total = fields.Float(string="Процент от выручки всех товаров")
    total_value = fields.Float(string="Значение по всем товарам")
