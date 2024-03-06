# -*- coding: utf-8 -*-
from ast import literal_eval

from odoo import models, fields, api


class OzonServices(models.Model):
    _name = "ozon.ozon_services"
    _description = "Дополнительные услуги Озон"

    name = fields.Char(string="Название услуги", readonly=True)
    price = fields.Float(string="Стоимость услуги", readonly=True)


class Transactions(models.Model):
    _name = "ozon.transaction"
    _description = "Транзакции"
    _order = "transaction_date desc"

    transaction_id = fields.Char(string="Идентификатор транзакции")
    transaction_date = fields.Date(string="Дата транзакции", readonly=True)
    order_date = fields.Date(
        string="Дата принятия отправления в обработку", readonly=True
    )
    name = fields.Char(string="Название транзакции", readonly=True)
    transaction_type = fields.Char(string="Тип транзакции", readonly=True)
    accruals_for_sale = fields.Float(string="Стоимость товаров с учётом скидок продавца", readonly=True)
    sale_commission = fields.Float(string="Комиссия за продажу или возврат комиссии за продажу", 
                                   readonly=True)
    amount = fields.Float(string="Итоговая сумма операции (стоимость - комиссия - стоимость доп.услуг)", 
                          readonly=True)
    skus = fields.Char(string="Список SKU товаров", readonly=True)
    products = fields.Many2many(
        "ozon.products",
        string="Товары",
        copy=True,
        readonly=True,
    )
    services = fields.Many2many(
        "ozon.ozon_services",
        string="Дополнительные услуги Ozon",
        copy=True,
        readonly=True,
    )
    posting_number = fields.Char(
        string="Номер отправления",
        readonly=True,
    )
    transaction_unit_ids = fields.One2many("ozon.transaction_unit", "transaction_id", 
                                           string="Составляющие транзакции")

    ozon_transaction_value_by_product_ids = fields.One2many("ozon.transaction.value_by_product", "transaction_id")

    def get_transactions_by_name_products_and_period(self, data):
        domain = []
        if name := data.get("name"):
            domain.append(("name", "=", name))
        if date_from := data.get("date_from"):
            domain.append(("transaction_date", ">=", fields.Date.to_date(date_from)))
        if date_to := data.get("date_to"):
            domain.append(("transaction_date", "<=", fields.Date.to_date(date_to)))
        if product_ids := data.get("product_ids"):
            domain.append(("products", "in", product_ids))
        if not domain:
            return
        return self.search(domain)
    
    @property
    def _skus(self) -> list:
        return [str(sku) for sku in literal_eval(self.skus)]
    
    @property
    def total_products_qty(self):
        return len(self._skus)
    
    @property
    def products_qty(self) -> dict:
        data = {}
        for p in self.products:
            qty = self._skus.count(p.sku) or self._skus.count(p.fbs_sku) or self._skus.count(p.fbo_sku)
            data.update({p: qty})
        return data
    
    def get_theory_acquiring(self):
        return sum([p._acquiring.value * qty for p, qty in self.products_qty.items()])
    

class TransactionUnit(models.Model):
    _name = "ozon.transaction_unit"
    _description = "Составляющая транзакции"

    transaction_id = fields.Many2one("ozon.transaction", string="Транзакция")
    transaction_date = fields.Date(related="transaction_id.transaction_date", store=True)
    transaction_name = fields.Char(related="transaction_id.name", store=True)
    transaction_type = fields.Char(related="transaction_id.transaction_type", store=True)
    name = fields.Char(string="Название")
    category = fields.Char(string="Категория", compute="_compute_category", store=True)
    value = fields.Float(string="Значение")

    indirect_percent_expenses_id = fields.Many2one("ozon.indirect_percent_expenses", 
                                                   string="Отчёт о косвенных затратах", 
                                                   ondelete="cascade")
    sales_report_by_category_id = fields.Many2one("ozon.sales_report_by_category", 
                                                   string="Отчёт о продажах категории", 
                                                   ondelete="cascade")
    @api.depends("name")
    def _compute_category(self):
        for r in self:
            if r.name in ["логистика", "последняя миля", "обработка отправления", 
                          "Обработка отправления «Pick-up» (отгрузка курьеру)",
                          "Услуги доставки Партнерами Ozon на схеме realFBS"]:
                r.category = "Обработка и доставка"
            else:
                r.category = r.name

    def collect_data_from_transactions(self, transactions) -> list:
        """Returns data to create."""
        data = []
        _ = len(transactions) - 1
        for idx, t in enumerate(transactions):
            t_id = t.id
            if t.name in ["Доставка покупателю", "Получение возврата, отмены, невыкупа от покупателя"]:
                data.extend([
                    {
                        "transaction_id": t_id,
                        "name": "Сумма за заказы",
                        "value": t.accruals_for_sale
                    },
                    {
                        "transaction_id": t_id,
                        "name": "Комиссия за продажу или возврат комиссии за продажу",
                        "value": t.sale_commission
                    },
                    {
                        "transaction_id": t_id,
                        "name": "Итого за заказы",
                        "value": t.amount
                    }
                ])
                for s in t.services:
                    data.append({
                        "transaction_id": t_id,
                        "name": s.name,
                        "value": s.price
                    })
            elif t.name in ["Доставка и обработка возврата, отмены, невыкупа", 
                            "Доставка покупателю — отмена начисления"]:
                for s in t.services:
                    data.append({
                        "transaction_id": t_id,
                        "name": s.name,
                        "value": s.price
                    })
            else:
                data.append({
                    "transaction_id": t_id,
                    "name": t.name,
                    "value": t.amount
                })
            print(f"{idx}/{_} - Transaction units data was collected")
        return data


class TransactionUnitSummary(models.Model):
    _name = "ozon.tran_unit_sum"
    _description = "Суммарные выплаты"

    name = fields.Char(string="Выплата")
    count = fields.Integer(string="Кол-во")
    value = fields.Float(string="Сумма")
    percent = fields.Float(string="Процент от выручки")

    indirect_percent_expenses_id = fields.Many2one("ozon.indirect_percent_expenses", 
                                                   string="Отчёт о выплатах", 
                                                   ondelete="cascade")
    sales_report_by_category_id = fields.Many2one("ozon.sales_report_by_category", 
                                                   string="Отчёт о продажах категории", 
                                                   ondelete="cascade")
    
    def collect_data_from_transaction_units(self, report, report_type):
        """
        Report types: 'indirect_percent_expenses_id', 'sales_report_by_category_id'
        """
        grouped_tran_units = self.env["ozon.transaction_unit"].read_group(
            domain=[(report_type, "=", report.id)], 
            fields=["name", "value"],
            groupby=["name"])
        rev = report.revenue
        data = [
            {"name": i["name"], 
             "count": i["name_count"], 
             "value": i["value"],
             "percent": i["value"] / rev if i["name"] not in ["Сумма за заказы", "Итого за заказы"] else 0, 
             report_type: report.id}
             for i in grouped_tran_units]
        return data


class TransactionValueByProduct(models.Model):
    _name = "ozon.transaction.value_by_product"
    _description = "Часть данных транзакции по продукту"

    transaction_id = fields.Many2one("ozon.transaction", string="Транзакция")
    transaction_date = fields.Date(related="transaction_id.transaction_date", store=True)
    transaction_name = fields.Char(related="transaction_id.name", store=True)
    transaction_type = fields.Char(related="transaction_id.transaction_type", store=True)
    name = fields.Char(string="Название")
    category = fields.Char(string="Категория", compute="_compute_category", store=True)
    value = fields.Float(string="Значение")

    ozon_products_id = fields.Many2one(
        "ozon.products",
        string="Товар",
        readonly=True,
    )

    @api.depends("name")
    def _compute_category(self):
        for r in self:
            if r.name in ["логистика", "последняя миля", "обработка отправления",
                          "Обработка отправления «Pick-up» (отгрузка курьеру)",
                          "Услуги доставки Партнерами Ozon на схеме realFBS"]:
                r.category = "Обработка и доставка"
            else:
                r.category = r.name
