# # -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
from itertools import chain

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
COEF_FIELDNAMES_STRINGS = {
    # "coef_promotion": "Услуги продвижения товаров",
    "coef_refund": "Получение возврата, отмены, невыкупа от покупателя",
    "coef_refund_delivery": "Доставка и обработка возврата, отмены, невыкупа",
    # "coef_pickup": "Обработка отправления «Pick-up» (отгрузка курьеру)",
    # "coef_acquiring": "Оплата эквайринга",
    # "coef_delivery_rfbs": "Услуги доставки Партнерами Ozon на схеме realFBS",
    # "coef_agent_rfbs": "Агентское вознаграждение за доставку Партнерами Ozon на схеме realFBS",
    # "coef_promotion_seller_bonus": "Услуга продвижения Бонусы продавца",
    # "coef_review": "Приобретение отзывов на платформе",
    # "coef_subscription_premium_plus": "Подписка Premium Plus",
    # "coef_seller_error_cancel": "Услуга за обработку операционных ошибок продавца: отмена",
    # "coef_seller_error_expired_shipment": "Услуга за обработку операционных ошибок продавца: просроченная отгрузка",
    # "coef_fbo_processing": "Обработка товара в составе грузоместа на FBO",
    # "coef_fbo_expiration_date_processing": "Обработка сроков годности на FBO",
    # "coef_utilization": "Утилизация",
    # "coef_booking_incomplete": "Услуга по бронированию места и персонала для поставки с неполным составом",
    # "coef_other": "Прочее",
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

    # TOTALS
    revenue = fields.Float(string="Выручка")
    total = fields.Float(string="Итого с учётом баллов")
    orders = fields.Float(string="Сумма за заказы")
    reward = fields.Float(string="Вознаграждение за продажу")
    processing_delivery = fields.Float(string="Обработка и доставка")
    returns_cancels = fields.Float(string="Возвраты и отмены")
    services = fields.Float(string="Доп.услуги")
    transfer = fields.Float(string="Перечисления")
    compensation = fields.Float(string="Компенсировано")
    other_total = fields.Float(string="Прочее")

    # BY TRANSACTION TYPE
    refund = fields.Float(
        string="Получение возврата, отмены, невыкупа от покупателя"
    )
    refund_delivery = fields.Float(
        string="Доставка и обработка возврата, отмены, невыкупа"
    )
    pickup = fields.Float(
        string="Обработка отправления «Pick-up» (отгрузка курьеру)"
    )
    acquiring = fields.Float(string="Оплата эквайринга")
    delivery_rfbs = fields.Float(
        string="Услуги доставки Партнерами Ozon на схеме realFBS"
    )
    agent_rfbs = fields.Float(
        string="Агентское вознаграждение за доставку Партнерами Ozon на схеме realFBS",
        readonly=True,
    )
    promotion_seller_bonus = fields.Float(
        string="Услуга продвижения Бонусы продавца"
    )
    review = fields.Float(string="Приобретение отзывов на платформе")
    subscription_premium_plus = fields.Float(
        string="Подписка Premium Plus"
    )
    seller_error_cancel = fields.Float(
        string="Услуга за обработку операционных ошибок продавца: отмена"
    )
    seller_error_expired_shipment = fields.Float(
        string="Услуга за обработку операционных ошибок продавца: просроченная отгрузка",
        readonly=True,
    )
    fbo_processing = fields.Float(
        string="Обработка товара в составе грузоместа на FBO"
    )
    fbo_expiration_date_processing = fields.Float(
        string="Обработка сроков годности на FBO"
    )
    utilization = fields.Float(string="Утилизация")
    booking_incomplete = fields.Float(
        string="Услуга по бронированию места и персонала для поставки с неполным составом",
        readonly=True,
    )
    other = fields.Float(string="Другие транзакции")

    # coefs: expenses/revenue
    coef_refund = fields.Float(
        string="Получение возврата, отмены, невыкупа от покупателя"
    )
    coef_refund_delivery = fields.Float(
        string="Доставка и обработка возврата, отмены, невыкупа"
    )
    coef_pickup = fields.Float(
        string="Обработка отправления «Pick-up» (отгрузка курьеру)"
    )
    coef_acquiring = fields.Float(string="Оплата эквайринга")
    coef_delivery_rfbs = fields.Float(
        string="Услуги доставки Партнерами Ozon на схеме realFBS"
    )
    coef_agent_rfbs = fields.Float(
        string="Агентское вознаграждение за доставку Партнерами Ozon на схеме realFBS",
        readonly=True,
    )
    coef_promotion_seller_bonus = fields.Float(
        string="Услуга продвижения Бонусы продавца"
    )
    coef_review = fields.Float(
        string="Приобретение отзывов на платформе"
    )
    coef_subscription_premium_plus = fields.Float(
        string="Подписка Premium Plus"
    )
    coef_seller_error_cancel = fields.Float(
        string="Услуга за обработку операционных ошибок продавца: отмена"
    )
    coef_seller_error_expired_shipment = fields.Float(
        string="Услуга за обработку операционных ошибок продавца: просроченная отгрузка",
        readonly=True,
    )
    coef_fbo_processing = fields.Float(
        string="Обработка товара в составе грузоместа на FBO"
    )
    coef_fbo_expiration_date_processing = fields.Float(
        string="Обработка сроков годности на FBO"
    )
    coef_utilization = fields.Float(string="Утилизация")
    coef_booking_incomplete = fields.Float(
        string="Услуга по бронированию места и персонала для поставки с неполным составом",
        readonly=True,
    )
    coef_other = fields.Float(string="Другие транзакции")

    # total
    coef_total = fields.Float(
        string="Общий коэффициент косвенных затрат"
    )

    def collect_data(self, date_from, date_to):
        domain = [("transaction_date", ">=", date_from), ("transaction_date", "<=", date_to)]
        transactions = self.env["ozon.transaction"].search(domain)
        
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
        _empty_products_orders = (orders - orders_other).filtered(lambda r: not r.products)

        for o in chain(orders - orders_other):
            print(o.products_qty)
        
        raise
        #
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
                     "revenue": accruals_for_sale, "total": total})
 
        transactions = self.env["ozon.transaction"].read_group(
            domain=[
                ("transaction_date", ">=", date_from),
                ("transaction_date", "<=", date_to),
            ],
            fields=[],
            groupby="name",
        )
        if not transactions:
            raise UserError("Транзакции за данный период не загружены.")            
        data.update({"other": 0, "coef_total": 0})

        for tran in transactions:
            name = tran["name"]
            if name in ["Услуги продвижения товаров"]:
                continue
            fieldname = STRING_FIELDNAMES.get(name)
            amount = tran["amount"]
            if amount > 0:
                continue
            if fieldname:
                data[fieldname] = amount
                data[f"coef_{fieldname}"] = abs(
                    round(amount / data["revenue"], 4) * 100
                )
            else:
                data["other"] += amount
        data["coef_other"] = abs(round(data["other"] / data["revenue"], 4) * 100)
        for k, v in data.items():
            if k.startswith("coef") and k not in ["coef_total", "coef_acquiring"]:
                data["coef_total"] += v
        return data

    def calculate_indirect_expenses_prev_month(self):
        """Запускать еженедельно на весь recordset ozon.products"""
        date_from = datetime.combine(datetime.now(), time.min) - timedelta(days=30)
        date_to = datetime.combine(datetime.now(), time.max) - timedelta(days=1)
        
        data = self.collect_data(date_from=date_from, date_to=date_to)
        rec = self.create(data)
        return rec

    # TODO: убрать после тестов
    def calculate(self):
        latest_indir_percent_expenses = self.calculate_indirect_expenses_prev_month()
        # all_products = self.env["ozon.products"].search([])
        # self.env["ozon.all_expenses"].update_all_expenses(all_products, latest_indir_percent_expenses)
        # self.env["ozon.products"].update_all_expenses()

    @api.model
    def create(self, values):
        data = self.collect_data(date_from=values["date_from"], date_to=values["date_to"])
        values.update(data)
        record = super(IndirectPercentExpenses, self).create(values)
        return record
    
    def write(self, values):
        date_from = values.get("date_from", self.date_from)
        date_to = values.get("date_to", self.date_to)
        data = self.collect_data(date_from, date_to)
        values.update(data)
        record = super(IndirectPercentExpenses, self).write(values)
        return record
    
    def name_get(self):
        """
        Rename records
        """
        result = []
        for record in self:
            result.append((record.id, f"С {record.date_from} по {record.date_to}"))
        return result
