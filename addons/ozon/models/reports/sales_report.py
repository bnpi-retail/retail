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
    
    
    @api.model
    def create(self, values):
        # Взять все товары из категории с продажами за период
        products = self.env["ozon.products"].get_products_by_cat_with_sales_for_period(values)
        Expense = namedtuple('Expense', ['name', 'category'])
        total_expenses = {}
        products_in_sales_report_ids, product_expenses_in_sales_report_data = [], []
        # транзакции "доставка покупателю" за период
        _ = {"name": "Доставка покупателю", "product_ids": products.ids}
        _.update(values)
        transactions = self.env["ozon.transaction"].get_transactions_by_name_products_and_period(_)

        # взять все затраты (all_expenses) по всем продуктам
        for p in products:
            prod_transactions = transactions.filtered(lambda r: p.id in r.products.ids)
            print(prod_transactions)
            sales_qty = len(prod_transactions)
            prod_revenue = sum(prod_transactions.mapped("accruals_for_sale"))
            expenses = p.all_expenses_ids.filtered(
                lambda r: r.category not in ["Рентабельность", "Investment", 
                                             "Вознаграждение Ozon", "Логистика", 
                                             "Последняя миля", "Обработка"]
            )
            sum_indir_expenses = sum(expenses.mapped("value")) * sales_qty
            sum_services = abs(sum(prod_transactions.services.mapped("price")))
            sum_commissions = abs(sum(prod_transactions.mapped("sale_commission")))
            prod_total_expenses = sum_indir_expenses + sum_services + sum_commissions
            prod_in_sales_report = self.env["ozon.product_in_sales_report"].create(
                {
                    "product_id": p.id,
                    "sales_count": sales_qty,
                    "revenue": prod_revenue,
                    "total_expenses": prod_total_expenses,
                    "profit": prod_revenue - prod_total_expenses,
                }
            )
            products_in_sales_report_ids.append(prod_in_sales_report.id)
            # комиссия за продажи
            exp = Expense(name="Комиссия за продажу", category="Вознаграждение Ozon")
            total_expenses.update({exp: total_expenses.get(exp, 0) + sum_commissions})
            exp_item = self.get_or_create_expenses_item(exp.name, exp.category)
            product_expenses_in_sales_report_data.append(
                    {
                        "product_in_sales_report_id": prod_in_sales_report.id,
                        "expenses_item_id": exp_item.id,
                        "expense": sum_commissions / sales_qty,
                        "total_expense": sum_commissions,
                    }
                )
            # фактические затраты (доп.услуги) из транзакций "Доставка покупателю"
            # group by name
            services = sorted(prod_transactions.services.read(["name", "price"]), key=itemgetter("name"))
            groupby_services = groupby(services, key=itemgetter("name"))
            for name, services in groupby_services:
                name = name.capitalize()
                total = abs(sum([i["price"] for i in list(services)]))
                # приплюсовать к total_expenses
                exp = Expense(name=name, category=name)
                total_expenses.update({exp: total_expenses.get(exp, 0) + total})
                # по каждому создать product_expenses_in_sales_report
                exp_item = self.get_or_create_expenses_item(name, name)
                product_expenses_in_sales_report_data.append(
                    {
                        "product_in_sales_report_id": prod_in_sales_report.id,
                        "expenses_item_id": exp_item.id,
                        "expense": total / sales_qty,
                        "total_expense": total,
                    }
                )
                
            
            # Косвенные затраты
            for e in expenses:
                exp = Expense(name=e.name, category=e.category)
                total_expenses.update({exp: total_expenses.get(exp, 0) + e.value * sales_qty})
                exp_item = self.get_or_create_expenses_item(e.name, e.category)
                product_expenses_in_sales_report_data.append(
                    {
                        "product_in_sales_report_id": prod_in_sales_report.id,
                        "expenses_item_id": exp_item.id,
                        "expense": e.value,
                        "total_expense": e.value * sales_qty,
                    }
                )
                
        prod_expenses_in_sales_report = self.env["ozon.prod_expenses_in_sales_report"].create(
            product_expenses_in_sales_report_data
        )
        
        # суммируем все затраты
        sum_total_expenses = sum(total_expenses.values())
        # рассчитываем profit
        total_revenue = sum(transactions.mapped("accruals_for_sale"))
        profit = total_revenue - sum_total_expenses
        expenses_by_category_data = []
        for k, v in total_expenses.items():
            exp_item = self.get_or_create_expenses_item(k.name, k.category)
            expenses_by_category_data.append(
                {
                    "expenses_item_id": exp_item.id, 
                    "expense": v, 
                }
            )
        expenses_by_category = self.env["ozon.expenses_by_category"].create(expenses_by_category_data)
        values.update(
            {
                "revenue": total_revenue,
                "total_expenses": sum_total_expenses,
                "profit": profit,
                "products_count": len(products),
                "sales_count": len(transactions),
                "expenses_by_category_ids": expenses_by_category.ids,
                "product_in_sales_report_ids": products_in_sales_report_ids,
            }
        )
        record = super(SalesReportByCategory, self).create(values)
        products_in_sales_report = self.env["ozon.product_in_sales_report"].browse(
            products_in_sales_report_ids)
        products_in_sales_report.sales_report_by_category_id = record.id
        prod_expenses_in_sales_report.sales_report_by_category_id = record.id
        expenses_by_category.sales_report_by_category_id = record.id
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