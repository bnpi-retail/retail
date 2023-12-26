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


class IndirectPercentExpenses(models.Model):
    _name = "ozon.indirect_percent_expenses"
    _description = "Косвенные затраты"

    timestamp = fields.Date(
        string="Дата расчета", default=fields.Date.today, readonly=True
    )
    date_from = fields.Datetime(string="Начало периода")
    date_to = fields.Datetime(string="Конец периода")

    # values
    revenue = fields.Float(string="Выручка", readonly=True)
    promotion = fields.Float(string="Услуги продвижения товаров", readonly=True)
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
    coef_promotion = fields.Float(string="Услуги продвижения товаров", readonly=True)
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

    def get_transactions_groups(self):
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
            name = tran["name"]
            fieldname = STRING_FIELDNAMES.get(name)
            amount = tran["amount"]

            if amount > 0:
                data["revenue"] += amount
            else:
                if fieldname:
                    data[fieldname] = amount
                    data[f"coef_{fieldname}"] = abs(round(amount / data["revenue"], 4))
                else:
                    data["other"] += amount

        data["coef_other"] = abs(round(data["other"] / data["revenue"], 4))

        for k, v in data.items():
            if k.startswith("coef") and k != "coef_total":
                data["coef_total"] += v

        self.create(data)

        total_coef = data["coef_total"]
        coef_percentage_string = f"{total_coef:.2%}"

        all_products = self.env["ozon.products"].search([])
        for i, product in enumerate(all_products):
            percent_expenses_records = []
            per_exp_record = self.env["ozon.cost"].create(
                {
                    "name": "Общий коэффициент косвенных затрат",
                    "price": round(product.price * total_coef, 2),
                    "discription": coef_percentage_string,
                    "product_id": product.id,
                }
            )
            percent_expenses_records.append(per_exp_record.id)
            # добавить к нему уже имеющуюся запись "Процент комиссии за продажу"
            sale_percent_com_record = product.percent_expenses.search(
                [
                    ("product_id", "=", product.id),
                    (
                        "name",
                        "in",
                        [
                            "Процент комиссии за продажу (FBO)",
                            "Процент комиссии за продажу (FBS)",
                        ],
                    ),
                ],
                limit=1,
            )
            if sale_percent_com_record:
                percent_expenses_records.append(sale_percent_com_record.id)

            product.percent_expenses = [(6, 0, percent_expenses_records)]

            if i % 100 == 0:
                self.env.cr.commit()
            print(
                f"{i} - Product {product.id_on_platform} percent expenses were updated."
            )
