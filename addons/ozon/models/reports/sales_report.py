from collections import namedtuple
from datetime import timedelta
from itertools import groupby
from operator import itemgetter

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
    product_in_sales_report_ids = fields.One2many("ozon.product_in_sales_report", 
        "sales_report_by_category_id", string="Товары в отчете", readonly=True)
    transaction_unit_ids = fields.One2many("ozon.transaction_unit", "sales_report_by_category_id",
                                           string="Составляющие транзакций")
    transaction_unit_summary_ids = fields.One2many("ozon.tran_unit_sum", "sales_report_by_category_id",
                                                    string="Суммарные выплаты")

    @api.model
    def create(self, values):
        # Взять все товары из категории с продажами за период
        products = self.env["ozon.products"].get_products_by_cat_with_sales_for_period(values)
        # Взять транзакции с данными продуктами за период
        _ = {"product_ids": products.ids}
        _.update(values)
        transactions = self.env["ozon.transaction"].get_transactions_by_name_products_and_period(_)
        sales = transactions.filtered(lambda r: r.name == "Доставка покупателю")
        sales_count = len(sales)
        products_count = len(products)
        tran_units_data = self.env["ozon.transaction_unit"].collect_data_from_transactions(transactions)
        tran_units = self.env["ozon.transaction_unit"].create(tran_units_data)
        revenue = sum(transactions.mapped("accruals_for_sale"))
        values.update({"revenue": revenue, "sales_count": sales_count, "products_count": products_count})
        rec = super(SalesReportByCategory, self).create(values)
        tran_units.sales_report_by_category_id = rec.id
        tran_unit_sum_model = self.env['ozon.tran_unit_sum']
        tran_unit_sum_data = tran_unit_sum_model.collect_data_from_transaction_units(
            report=rec, report_type="sales_report_by_category_id")
        tran_unit_sum_recs = tran_unit_sum_model.create(tran_unit_sum_data)
        total_expenses = sum(tran_unit_sum_recs.filtered(lambda r: r.value < 0).mapped("value"))
        profit = revenue + total_expenses
        rec.write({"total_expenses": total_expenses, "profit": profit})
        return rec

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
    
    def open_pivot_view_expenses_by_product(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Затраты по товарам",
            "view_mode": "pivot",
            "res_model": "ozon.prod_expenses_in_sales_report",
            "domain": [("sales_report_by_category_id", "=", self.id)],
            "context": {},
        }
    

    def open_pivot_view_revenue_by_product(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Выручка и кол-во продаж по товарам",
            "view_mode": "pivot",
            "res_model": "ozon.product_in_sales_report",
            "domain": [("sales_report_by_category_id", "=", self.id)],
            "context": {},
        }
    
    def get_or_create_expenses_item(self, name, category):
        if exp_item := self.env["ozon.expenses_item"].search(
            [("name", "=", name), ("category", "=", category)]
        ):
            pass
        else:
            exp_item = self.env["ozon.expenses_item"].create(
                {
                    "name": name, "category": category,
                }
            )
        return exp_item
    

class ExpensesItem(models.Model):
    _name = "ozon.expenses_item"
    _description = "Статья затрат"
    
    name = fields.Char(string="Статья затрат", readonly=True)
    category = fields.Char(string="Категория", readonly=True)


class ExpensesByCategory(models.Model):
    _name = "ozon.expenses_by_category"
    _description = "Затраты по категории за период"
    _order= "expense desc"

    expenses_item_id = fields.Many2one("ozon.expenses_item", string="Статья затрат")
    expense = fields.Float(string="Сумма")
    sales_report_by_category_id = fields.Many2one(
        "ozon.sales_report_by_category", string="Отчет по продажам категории"
    )

    def name_get(self):
        result = []
        for r in self:
            result.append(
                (
                    r.id,
                    f"""{r.expenses_item_id.name}""",
                )
            )
        return result


class ProductsInSalesReport(models.Model):
    _name = "ozon.product_in_sales_report"
    _description = "Товар в отчете по продажам категории"

    sales_report_by_category_id = fields.Many2one("ozon.sales_report_by_category", string="Отчет")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    sales_count = fields.Integer(string="Кол-во продаж", readonly=True)
    revenue = fields.Float(string="Выручка", readonly=True)
    total_expenses = fields.Float(string="Итого затрат", readonly=True)
    profit = fields.Float(string="Прибыль")
    prod_expenses_in_sales_report_ids = fields.One2many("ozon.prod_expenses_in_sales_report",
        "product_in_sales_report_id", string="Затраты по товару")
    

class ProductsExpensesInSalesReport(models.Model):
    _name = "ozon.prod_expenses_in_sales_report"
    _description = "Затраты по товарам в отчете по продажам категории"
    _order= "expense desc"

    sales_report_by_category_id = fields.Many2one("ozon.sales_report_by_category", string="Отчет")
    product_in_sales_report_id = fields.Many2one("ozon.product_in_sales_report", 
                                                 string="Товар в отчете")
    expenses_item_id = fields.Many2one("ozon.expenses_item", string="Статья затрат")
    expense = fields.Float(string="Затраты на ед. товара")
    total_expense = fields.Float(string="Сумма")