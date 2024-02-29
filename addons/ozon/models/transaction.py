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