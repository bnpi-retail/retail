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
    expenses_by_category_ids = fields.One2many(
        "ozon.expenses_by_category",
        "sales_report_by_category_id",
        string="Статьи затрат",
        readonly=True,
    )
    revenue = fields.Float(string="Выручка за период", readonly=True)
    total_expenses = fields.Float(string="Затраты за период", readonly=True)
    profit = fields.Float(string="Прибыль за период", readonly=True)

    @api.model
    def create(self, values):
        date_from = fields.Date.to_date(values["date_from"])
        date_to = fields.Date.to_date(values["date_to"])
        cat_id = values["category_id"]
        # Взять все товары из категории
        products = self.env["ozon.products"].search([("categories", "=", cat_id),("sales","!=",False)])
        print(len(products))
        total_revenue = 0
        total_expenses = {}
        # взять все затраты (all_expenses) по всем продуктам
        for p in products:
            sales = p.mapped("sales").filtered(lambda r: date_from <= r.date <= date_to)
            sales_qty = len(sales)
            if sales_qty == 0:
                continue
            total_revenue += sum(sales.mapped("revenue"))
            expenses = p.all_expenses_ids.filtered(
                lambda r: r.category not in ["Рентабельность", "Investment"]
            )
            # TODO: FIX когда себестоимость - не нужно умножать
            for e in expenses:
                total_expenses.update(
                    {
                        e.category: total_expenses.get(e.category, 0)
                        + e.value * sales_qty
                    }
                )

        # суммируем все затраты
        sum_total_expenses = sum(total_expenses.values())
        # рассчитываем profit
        profit = total_revenue - sum_total_expenses

        values.update(
            {
                "revenue": total_revenue,
                "total_expenses": sum_total_expenses,
                "profit": profit,
            }
        )
        record = super(SalesReportByCategory, self).create(values)
        expenses_by_category = self.env["ozon.expenses_by_category"].create(
            [
                {"name": k, "expense": v, "sales_report_by_category_id": record.id}
                for k, v in total_expenses.items()
            ]
        )
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


class ExpensesByCategory(models.Model):
    _name = "ozon.expenses_by_category"
    _description = "Затраты по категории за период"

    name = fields.Char(string="Статья затрат")
    expense = fields.Float(string="Сумма")
    sales_report_by_category_id = fields.Many2one(
        "ozon.sales_report_by_category", string="Отчет по продажам категории"
    )
