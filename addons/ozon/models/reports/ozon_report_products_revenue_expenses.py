from odoo import models, fields


class OzonReportProductsRevenueExpenses(models.Model):
    _name = "ozon.report.products_revenue_expenses"
    _description = "Строки отчета по выручке и расходах продукта за период внутри продукта"

    identifier = fields.Integer(string="Идентификатор")
    ozon_products_id = fields.Many2one("ozon.products", string="Товар Ozon")
    ozon_categories_id = fields.Many2one("ozon.categories", string="Категория Ozon")
    name = fields.Char(string="Название")
    comment = fields.Text(string="Комментарий", readonly=True)
    value = fields.Float(string="Товар")
    qty = fields.Integer(string="Количество")
    percent = fields.Float(string="Процент")
    percent_from_total = fields.Float(string="Процент")
    total_value = fields.Float(string="Магазин")
    percent_from_total_category = fields.Float(string="Процент")
    total_value_category = fields.Float(string="Категория")
    accuracy = fields.Char(size=2)


class OzonReportProductsRevenueExpensesTheory(models.Model):
    _name = "ozon.report.products_revenue_expenses_theory"
    _description = "Строки отчета по выручке и расходах продукта за период внутри продукта c теоретическими значениями"

    identifier = fields.Integer(string="Идентификатор")
    ozon_products_id = fields.Many2one("ozon.products", string="Товар Ozon")
    ozon_categories_id = fields.Many2one("ozon.categories", string="Категория Ozon")
    name = fields.Char(string="Название")
    comment = fields.Text(string="Комментарий", readonly=True)
    value = fields.Float(string="Товар")
    qty = fields.Integer(string="Количество")
    percent = fields.Float(string="Процент")
    percent_from_total_category = fields.Float(string="Процент")
    total_value_category = fields.Float(string="Категория")
    theoretical_value = fields.Char(string="Теория")


class OzonNameValue(models.Model):
    _name = "ozon.name_value"
    _description = "name- value model"

    ozon_categories_id = fields.Many2one("ozon.categories", string="Категория Ozon")
    name = fields.Char(string="Название")
    value = fields.Integer(string="Товар")
    domain = fields.Char(size=2)


