# # -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
from odoo import models, fields, api, exceptions

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
    "coef_pickup": "Обработка отправления «Pick-up» (отгрузка курьеру)",
    # "coef_acquiring": "Оплата эквайринга",
    "coef_delivery_rfbs": "Услуги доставки Партнерами Ozon на схеме realFBS",
    "coef_agent_rfbs": "Агентское вознаграждение за доставку Партнерами Ozon на схеме realFBS",
    "coef_promotion_seller_bonus": "Услуга продвижения Бонусы продавца",
    "coef_review": "Приобретение отзывов на платформе",
    "coef_subscription_premium_plus": "Подписка Premium Plus",
    "coef_seller_error_cancel": "Услуга за обработку операционных ошибок продавца: отмена",
    "coef_seller_error_expired_shipment": "Услуга за обработку операционных ошибок продавца: просроченная отгрузка",
    "coef_fbo_processing": "Обработка товара в составе грузоместа на FBO",
    "coef_fbo_expiration_date_processing": "Обработка сроков годности на FBO",
    "coef_utilization": "Утилизация",
    "coef_booking_incomplete": "Услуга по бронированию места и персонала для поставки с неполным составом",
    "coef_other": "Прочее",
}


class IndirectPercentExpenses(models.Model):
    _name = "ozon.indirect_percent_expenses"
    _description = "Косвенные затраты"
    _order = "create_date desc"

    timestamp = fields.Date(
        string="Дата расчета", default=fields.Date.today, readonly=True
    )
    date_from = fields.Date(string="Начало периода", readonly=True)
    date_to = fields.Date(string="Конец периода", readonly=True)

    # values
    revenue = fields.Float(string="Выручка", readonly=True)
    refund = fields.Float(
        string="Получение возврата, отмены, невыкупа от покупателя", readonly=True
    )
    refund_delivery = fields.Float(
        string="Доставка и обработка возврата, отмены, невыкупа", readonly=True
    )
    pickup = fields.Float(
        string="Обработка отправления «Pick-up» (отгрузка курьеру)", readonly=True
    )
    acquiring = fields.Float(string="Оплата эквайринга", readonly=True)
    delivery_rfbs = fields.Float(
        string="Услуги доставки Партнерами Ozon на схеме realFBS", readonly=True
    )
    agent_rfbs = fields.Float(
        string="Агентское вознаграждение за доставку Партнерами Ozon на схеме realFBS",
        readonly=True,
    )
    promotion_seller_bonus = fields.Float(
        string="Услуга продвижения Бонусы продавца", readonly=True
    )
    review = fields.Float(string="Приобретение отзывов на платформе", readonly=True)
    subscription_premium_plus = fields.Float(
        string="Подписка Premium Plus", readonly=True
    )
    seller_error_cancel = fields.Float(
        string="Услуга за обработку операционных ошибок продавца: отмена", readonly=True
    )
    seller_error_expired_shipment = fields.Float(
        string="Услуга за обработку операционных ошибок продавца: просроченная отгрузка",
        readonly=True,
    )
    fbo_processing = fields.Float(
        string="Обработка товара в составе грузоместа на FBO", readonly=True
    )
    fbo_expiration_date_processing = fields.Float(
        string="Обработка сроков годности на FBO", readonly=True
    )
    utilization = fields.Float(string="Утилизация", readonly=True)
    booking_incomplete = fields.Float(
        string="Услуга по бронированию места и персонала для поставки с неполным составом",
        readonly=True,
    )
    other = fields.Float(string="Прочее", readonly=True)

    # coefs: expenses/revenue
    coef_refund = fields.Float(
        string="Получение возврата, отмены, невыкупа от покупателя", readonly=True
    )
    coef_refund_delivery = fields.Float(
        string="Доставка и обработка возврата, отмены, невыкупа", readonly=True
    )
    coef_pickup = fields.Float(
        string="Обработка отправления «Pick-up» (отгрузка курьеру)", readonly=True
    )
    coef_acquiring = fields.Float(string="Оплата эквайринга", readonly=True)
    coef_delivery_rfbs = fields.Float(
        string="Услуги доставки Партнерами Ozon на схеме realFBS", readonly=True
    )
    coef_agent_rfbs = fields.Float(
        string="Агентское вознаграждение за доставку Партнерами Ozon на схеме realFBS",
        readonly=True,
    )
    coef_promotion_seller_bonus = fields.Float(
        string="Услуга продвижения Бонусы продавца", readonly=True
    )
    coef_review = fields.Float(
        string="Приобретение отзывов на платформе", readonly=True
    )
    coef_subscription_premium_plus = fields.Float(
        string="Подписка Premium Plus", readonly=True
    )
    coef_seller_error_cancel = fields.Float(
        string="Услуга за обработку операционных ошибок продавца: отмена", readonly=True
    )
    coef_seller_error_expired_shipment = fields.Float(
        string="Услуга за обработку операционных ошибок продавца: просроченная отгрузка",
        readonly=True,
    )
    coef_fbo_processing = fields.Float(
        string="Обработка товара в составе грузоместа на FBO", readonly=True
    )
    coef_fbo_expiration_date_processing = fields.Float(
        string="Обработка сроков годности на FBO", readonly=True
    )
    coef_utilization = fields.Float(string="Утилизация", readonly=True)
    coef_booking_incomplete = fields.Float(
        string="Услуга по бронированию места и персонала для поставки с неполным составом",
        readonly=True,
    )
    coef_other = fields.Float(string="Прочее", readonly=True)

    # total
    coef_total = fields.Float(
        string="Общий коэффициент косвенных затрат", readonly=True
    )

    def calculate_indirect_expenses_prev_month(self):
        """Запускать еженедельно на весь recordset ozon.products"""
        date_from = datetime.combine(datetime.now(), time.min) - timedelta(days=30)
        date_to = datetime.combine(datetime.now(), time.max) - timedelta(days=1)
        transactions = self.env["ozon.transaction"].read_group(
            domain=[
                ("transaction_date", ">=", date_from),
                ("transaction_date", "<=", date_to),
            ],
            fields=[],
            groupby="name",
        )

        data = {
            "date_from": date_from,
            "date_to": date_to,
            "revenue": 0,
            "other": 0,
            "coef_total": 0,
        }
        for tran in transactions:
            if tran["amount"] > 0:
                data["revenue"] += tran["amount"]

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

        self.create(data)

    # TODO: убрать после тестов
    def calculate(self):
        self.calculate_indirect_expenses_prev_month()
        self.env["ozon.products"].update_all_expenses()

    def name_get(self):
        """
        Rename records
        """
        result = []
        for record in self:
            result.append((record.id, f"С {record.date_from} по {record.date_to}"))
        return result
