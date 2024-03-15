# # -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
from itertools import chain
from operator import iadd, isub

from odoo import models, fields, api
from odoo.exceptions import UserError

STRING_FIELDNAMES = {
    "Выручка": "revenue",
    "Услуги продвижения товаров": "promotion",
    "Получение возврата, отмены, невыкупа от покупателя": "refund",
    "Доставка и обработка возврата, отмены, невыкупа": "refund_delivery",
    "Обработка отправления «Pick-up» (отгрузка курьеру)": "pickup",
    "Оплата эквайринга": "acquiring",
    "Услуги доставки Партнерами Ozon на схеме realFBS": "delivery_rfbs",
    "Агентское вознаграждение за доставку Партнерами Ozon на схеме realFBS": "agent_rfbs",
    "Услуга продвижения Бонусы продавца": "promotion_seller_bonus",
    "Приобретение отзывов на платформе": "review",
    "Подписка Premium Plus": "subscription_premium_plus",
    "Услуга за обработку операционных ошибок продавца: отмена": "seller_error_cancel",
    "Услуга за обработку операционных ошибок продавца: просроченная отгрузка": "seller_error_expired_shipment",
    "Обработка товара в составе грузоместа на FBO": "fbo_processing",
    "Обработка сроков годности на FBO": "fbo_expiration_date_processing",
    "Утилизация": "utilization",
    "Услуга по бронированию места и персонала для поставки с неполным составом": "booking_incomplete",
    "Прочее": "other",
}


class IndirectPercentExpenses(models.Model):
    _name = "ozon.indirect_percent_expenses"
    _description = "Косвенные затраты"
    _order = "create_date desc"

    timestamp = fields.Date(
        string="Дата расчета", default=fields.Date.today
    )
    date_from = fields.Date(string="Начало периода")
    date_to = fields.Date(string="Конец периода")
    
    transaction_unit_ids = fields.Many2many("ozon.transaction_unit", 
                                           string="Составляющие транзакций")
    transaction_unit_summary_ids = fields.One2many("ozon.tran_unit_sum", "indirect_percent_expenses_id",
                                                    string="Суммарные выплаты")
    # FACT TOTALS
    revenue = fields.Float(string="Выручка")
    total = fields.Float(string="Итого с учётом баллов")
    orders = fields.Float(string="Сумма за заказы (заказы+возвраты)")
    reward = fields.Float(string="Вознаграждение за продажу")
    processing_delivery = fields.Float(string="Обработка и доставка")
    returns_cancels = fields.Float(string="Возвраты и отмены")
    services = fields.Float(string="Доп.услуги")
    transfer = fields.Float(string="Перечисления")
    compensation = fields.Float(string="Компенсировано")
    other_total = fields.Float(string="Прочее (эквайринг)")

    # THEORY TOTALS
    theory_processing_delivery = fields.Float(string="Обработка и доставка (теоретическое значение)")
    theory_acquiring = fields.Float(string="Эквайринг (теоретическое значение)")


    def collect_data(self, date_from, date_to):
        domain = [("transaction_date", ">=", date_from), ("transaction_date", "<=", date_to)]
        tran_model = self.env["ozon.transaction"]
        transactions = tran_model.search(domain)
        tran_units_data = self.env["ozon.transaction_unit"].collect_data_from_transactions(transactions)
        
        # Заказы
        orders = transactions.filtered(lambda r: r.transaction_type == "заказы")
        orders_other = orders.filtered(lambda r: r.name != "Доставка покупателю")
        total_orders_other_amount = sum(orders_other.mapped("amount"))
        accruals_for_sale = sum(orders.mapped("accruals_for_sale"))
        sale_commission = sum(orders.mapped("sale_commission"))
        orders_processing_and_delivery = sum(orders.services.mapped("price"))

        # Возвраты и отмены 
        returns_and_cancels = transactions.filtered(lambda r: r.transaction_type == "возвраты и отмены")
        returns_and_cancels_accruals = sum(returns_and_cancels.mapped("accruals_for_sale"))
        returns_and_cancels_sale_com = sum(returns_and_cancels.mapped("sale_commission"))
        returns_and_cancels_amount = sum(returns_and_cancels.mapped("amount"))
        returns_and_cancels_proc_and_deliv = sum(returns_and_cancels.services.filtered(lambda r: r.name in ['последняя миля', 'обработка отправления', 'логистика']).mapped("price"))

        # Сколько заказов с sku, которых у нас нет
        # _empty_products_orders = (orders - orders_other).filtered(lambda r: not r.products)

        proc_and_deliv = (orders_processing_and_delivery 
                          + total_orders_other_amount 
                          + returns_and_cancels_proc_and_deliv)
        ret_and_cancels = (abs(returns_and_cancels_accruals - returns_and_cancels_amount) 
                           - returns_and_cancels_sale_com 
                           - returns_and_cancels_proc_and_deliv)
        services = sum(transactions.filtered(lambda r: r.transaction_type == "сервисные сборы").mapped("amount"))
        transfer = sum(transactions.filtered(lambda r: r.transaction_type == "transfer_delivery").mapped("amount"))
        compensation = sum(transactions.filtered(lambda r: r.transaction_type == "компенсация").mapped("amount"))
        other_total = sum(transactions.filtered(lambda r: r.transaction_type == "прочее").mapped("amount"))
        sum_orders = accruals_for_sale + returns_and_cancels_accruals
        reward = sale_commission + returns_and_cancels_sale_com
        
        # THEORY
        # theory_processing_and_delivery: Рассчитываем какие были бы затраты на логистику/обработку, если б мы считали из теоретических данных (из карточки продукта)
        theory_last_mile = 0
        theory_logistics = 0
        theory_processing = 0
        for o in chain(
            (orders - orders_other), returns_and_cancels.filtered(
                lambda r: r.name == "Доставка покупателю — отмена начисления")
                ):
            if o.transaction_type == "заказы":
                oper = isub
                prod_qty = o.products_qty.items()
            elif o.transaction_type == "возвраты и отмены":
                oper = iadd
                sale = tran_model.search(
                    [("posting_number", "=", o.posting_number), ("name", "=", "Доставка покупателю")], limit=1)
                prod_qty = sale.products_qty.items()
            s_names = o.services.filtered(lambda r: r.price != 0).mapped("name")
            for n in s_names:
                if n == "логистика":
                    theory_logistics = oper(
                        theory_logistics, sum([sum(p._logistics.mapped("value")) * qty for p, qty in prod_qty]))
                elif n == "обработка отправления":
                    theory_processing = oper(
                        theory_processing, sum([sum(p._processing.mapped("value")) * qty for p, qty in prod_qty]))
                elif n == "последняя миля":
                    theory_last_mile = oper(
                        theory_last_mile, sum([p._last_mile.value * qty for p, qty in prod_qty]))
        theory_proc_and_deliv = theory_last_mile + theory_logistics + theory_processing

        # theory_acquiring
        theory_acquiring = -sum(t.get_theory_acquiring() for t in transactions.filtered(
            lambda r: r.name == "Оплата эквайринга"))

        data = {
            "orders": sum_orders,
            "reward": reward,
            "processing_delivery": proc_and_deliv,
            "returns_cancels": ret_and_cancels,
            "services": services,
            "transfer": transfer,
            "compensation": compensation,
            "other_total": other_total
        }
        total = sum(data.values())
        data.update({"date_from": date_from, "date_to": date_to, 
                     "revenue": accruals_for_sale, "total": total, 
                     "theory_processing_delivery": theory_proc_and_deliv,
                     "theory_acquiring": theory_acquiring})
 
        return data, tran_units_data

    def calculate_indirect_expenses_prev_month(self):
        """Запускать еженедельно на весь recordset ozon.products"""
        date_from = datetime.combine(datetime.now(), time.min) - timedelta(days=30)
        date_to = datetime.combine(datetime.now(), time.max) - timedelta(days=1)
        
        data, transaction_units_data = self.collect_data(date_from=date_from, date_to=date_to)
        rec = self.create(data)
        return rec



    @api.model
    def create(self, values):
        data, transaction_units_data = self.collect_data(values["date_from"], values["date_to"])
        # tran_units = self.env["ozon.transaction_unit"].create(transaction_units_data)
        values.update(data)
        rec = super(IndirectPercentExpenses, self).create(values)
        # tran_units.indirect_percent_expenses_id = rec.id
        tran_unit_sum_model = self.env['ozon.tran_unit_sum']
        tran_unit_sum_data = tran_unit_sum_model.collect_data_from_decomposed_transactions(
            values["date_from"], values["date_to"])
        tran_unit_sum_recs = tran_unit_sum_model.create(tran_unit_sum_data)
        tran_unit_sum_recs.write({"indirect_percent_expenses_id": rec.id})
        return rec
    
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, f"С {record.date_from} по {record.date_to}"))
        return result

    def open_transaction_unit_view(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Разбивка транзакций на услуги",
            "view_mode": "tree,form",
            "res_model": "ozon.transaction_unit",
            "domain": [("indirect_percent_expenses_id", "=", self.id)],
            "context": {"create": False},
        }

    def open_decomposed_transactions_view(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Декомпозированные транзакции",
            "view_mode": "tree,form",
            "res_model": "ozon.transaction.value_by_product",
            "domain": [("transaction_date", ">=", self.date_from), 
                       ("transaction_date", "<=", self.date_to)],
            "context": {"create": False},
        }

    def get_latest(self):
        return self.search([], limit=1, order="create_date desc")