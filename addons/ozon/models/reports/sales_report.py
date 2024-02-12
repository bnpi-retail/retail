from collections import namedtuple
from datetime import timedelta

from odoo import models, fields, api


class SalesReportByCategory(models.Model):
    _name = "ozon.sales_report_by_category"
    _description = "Отчёт по продажам категории"
    _order = "create_date desc"

    category_id = fields.Many2one(
        "ozon.categories", string="Категория товаров", required=True
    )
    date_from = fields.Date(
        string="Начало периода", default=fields.Date.today() - timedelta(days=30)
    )
    date_to = fields.Date(string="Конец периода", default=fields.Date.today)
    expenses_by_category_ids = fields.Many2many(
        "ozon.expenses_by_category",
        string="Статьи затрат",
        readonly=True,
    )
    revenue = fields.Float(string="Выручка за период", readonly=True)
    total_expenses = fields.Float(string="Затраты за период", readonly=True)
    profit = fields.Float(string="Прибыль за период", readonly=True)
    products_count = fields.Integer(string="Кол-во товаров, у которых были продажи", readonly=True)
    sales_count = fields.Integer(string="Кол-во продаж", readonly=True)

    @api.model
    def create(self, values):
        date_from = fields.Date.to_date(values["date_from"])
        date_to = fields.Date.to_date(values["date_to"])
        cat_id = values["category_id"]
        # Взять все товары из категории
        products = self.env["ozon.products"].search([("categories", "=", cat_id), ("sales", "!=", False)])
        Expense = namedtuple('Expense', ['name', 'category'])
        total_revenue = 0
        total_expenses = {}
        total_products_count = 0
        total_sales_count = 0
        # взять все затраты (all_expenses) по всем продуктам
        for p in products:
            sales = p.mapped("sales").filtered(lambda r: date_from <= r.date <= date_to)
            sales_qty = len(sales)
            if sales_qty == 0:
                continue
            total_products_count += 1
            total_sales_count += sales_qty
            total_revenue += sum(sales.mapped("revenue"))
            expenses = p.all_expenses_ids.filtered(
                lambda r: r.category not in ["Рентабельность", "Investment"]
            )
            for e in expenses:
                exp = Expense(name=e.name, category=e.category)
                total_expenses.update(
                    {
                        exp: total_expenses.get(exp, 0)
                        + e.value * sales_qty
                    }
                )

        # суммируем все затраты
        sum_total_expenses = sum(total_expenses.values())
        # рассчитываем profit
        profit = total_revenue - sum_total_expenses
        expenses_by_category = self.env["ozon.expenses_by_category"].create(
            [
                {
                    "name": k.name, 
                    "category": k.category, 
                    "expense": v, 
                 }
                for k, v in total_expenses.items()
            ]
        )
        values.update(
            {
                "revenue": total_revenue,
                "total_expenses": sum_total_expenses,
                "profit": profit,
                "products_count": total_products_count,
                "sales_count": total_sales_count,
                "expenses_by_category_ids": expenses_by_category.ids, 
            }
        )
        record = super(SalesReportByCategory, self).create(values)
        
        return record

    def name_get(self):
        result = []
        for r in self:
            result.append(
                (
                    r.id,
                    f"""Продажи в категории "{r.category_id.name_categories}" c {r.date_from.strftime("%d %b %Y")} по {r.date_to.strftime("%d %b %Y")}""",
                )
            )
        return result
    
    def show_expenses(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Затраты",
            "view_mode": "tree",
            "res_model": "ozon.expenses_by_category",
            "domain": [("sales_report_by_category_id", "=", self.id)],
            "context": {"group_by": "category", "create": False},
            "target": "new",
        }

    def open_pivot_view(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Подробнее",
            "view_mode": "pivot",
            "res_model": "ozon.sales_report_by_category",
            "domain": [("id", "=", self.id)],
            "context": {},
            "target": "new",
        }

class ExpensesByCategory(models.Model):
    _name = "ozon.expenses_by_category"
    _description = "Затраты по категории за период"
    _order= "expense desc"

    name = fields.Char(string="Статья затрат")
    category = fields.Char(string="Категория", readonly=True)
    expense = fields.Float(string="Сумма")
    sales_report_by_category_id = fields.Many2one(
        "ozon.sales_report_by_category", string="Отчет по продажам категории"
    )

class ProductsInExpensesByCategory(models.Model):
    _name = "ozon.prod_in_expenses_by_cat"
    _description = "Затраты по продуктам в затратах по категории за период"
    _order= "expense desc"

    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    expense = fields.Float(string="Сумма")