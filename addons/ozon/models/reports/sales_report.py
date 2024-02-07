from odoo import models, fields


class SalesReportByCategory(models.Model):
    _name = "ozon.sales_report_by_category"
    _description = "Отчёт по продажам категории"

    category_id = fields.Many2one("ozon.categories", string="Категория товаров")
    date_from = fields.Date(string="Начало периода")
    date_to = fields.Date(string="Конец периода")
    all_expenses_by_category_ids = fields.One2many(
        "ozon.expenses_by_category",
        "sales_report_by_category_id",
        string="Статьи затрат",
    )
    revenue = fields.Float(string="Выручка за период")
    profit = fields.Float(string="Прибыль за период")


class ExpensesByCategory(models.Model):
    _name = "ozon.expenses_by_category"
    _description = "Затраты по категории за период"

    name = fields.Char(string="Статья расходов")
    expense = fields.Float(string="Расход")
    sales_report_by_category_id = fields.Many2one(string="Отчет по продажам категории")
