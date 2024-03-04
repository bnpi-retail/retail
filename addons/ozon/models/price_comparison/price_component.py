from odoo import models, fields, api

NAME_IDENTIFIER = {
    "Цена для покупателя": "buyer_price",
    "Ваша цена": "your_price",
    "Себестоимость": "cost",
    "Логистика": "logistics",
    "Последняя миля": "last_mile",
    "Эквайринг": "acquiring",
    "Вознаграждение Ozon": "ozon_reward",
    "Реклама": "promo",
    "Обработка": "processing",
    "Обратная логистика": "return_logistics",
    "Обработка и хранение (компания)": "company_processing_and_storage",
    "Упаковка (компания)": "company_packaging",
    "Маркетинг (компания)": "company_marketing",
    "Операторы (компания)": "company_operators",
    "Налог": "tax",
    "Сумма расходов": "total_expenses",
    "Прибыль": "profit",
    "ROS (доходность, рентабельность продаж)": "ros",
    "Наценка": "margin",
    "Процент наценки": "margin_percent",
    "ROE (рентабельность инвестиций)": "roe",
}

IDENTIFIER_NAME = {
     "buyer_price": "Цена для покупателя",
     "your_price": "Ваша цена",
     "cost": "Себестоимость",
     "logistics": "Логистика",
     "last_mile": "Последняя миля",
     "acquiring": "Эквайринг",
     "ozon_reward": "Вознаграждение Ozon",
     "promo": "Реклама",
     "processing": "Обработка",
     "return_logistics": "Обратная логистика",
     "company_processing_and_storage": "Обработка и хранение (компания)",
     "company_packaging": "Упаковка (компания)",
     "company_marketing": "Маркетинг (компания)",
     "company_operators": "Операторы (компания)",
     "tax": "Налог",
     "total_expenses": "Сумма расходов",
     "profit": "Прибыль",
     "ros": "ROS (доходность, рентабельность продаж)",
     "margin": "Наценка",
     "margin_percent": "Процент наценки",
     "roe": "ROE (рентабельность инвестиций)",
 }

BASE_CALCULATION_COMPONENTS = [
    "cost",
    "logistics", 
    "last_mile", 
    "acquiring", 
    "ozon_reward", 
    "promo", 
    "processing", 
    "return_logistics", 
    "company_processing_and_storage", 
    "company_packaging",
    "company_marketing",
    "company_operators",
    "tax",
    "roe",
    ]
PERCENT_COMPONENTS = [
    "last_mile", 
    "acquiring", 
    "ozon_reward", 
    "promo",
    "tax"
]
DEPENDS_ON_VOLUME_COMPONENTS = [
    "logistics"
]
PERCENT_COST_PRICE_COMPONENTS = [
    "roe"
]

class PriceComponent(models.Model):
    _name = "ozon.price_component"
    _description = "Компонент цены"

    name = fields.Char(string="Название")
    identifier = fields.Char(string="Идентификатор", readonly=True)

    def get(self, identifier):
        component = self.search([("identifier", "=", identifier)])
        if not component:
            component = self.create({"identifier": identifier, 
                                     "name": IDENTIFIER_NAME.get(identifier, identifier)})
        return component

    def fill_model(self):
        all_components = self.env["ozon.price_component"].search([])
        if len(all_components) == len(NAME_IDENTIFIER):
            return
        self.create(
            [
                {"identifier": iden, "name": name}
                for name, iden in NAME_IDENTIFIER.items()
            ]
        )
FACT_PLAN_MATCH = {
    "логистика": "logistics",
    "магистраль": "logistics",
    "Услуги доставки Партнерами Ozon на схеме realFBS": "logistics",
    "Агентское вознаграждение за доставку Партнерами Ozon на схеме realFBS": "logistics",
    "последняя миля": "last_mile",
    "Оплата эквайринга": "acquiring",
    "Комиссия за продажу или возврат комиссии за продажу": "ozon_reward",
    "Услуги продвижения товаров": "promo",
    "обработка отправления": "processing",
    "сборка заказа": "processing",
    "Обработка отправления «Pick-up» (отгрузка курьеру)": "processing",
    "обработка возврата": "processing",
    "обработка невыкупа": "processing",
    "обработка отмен": "processing",
    "обратная магистраль": "return_logistics",
    "обратная логистика": "return_logistics",
    "MarketplaceServiceItemRedistributionReturnsPVZ": "return_logistics",
    "Начисление по спору": None,
    "Начисления по претензиям": None,
    "Перечисление за доставку от покупателя": None,
    "Подписка Premium Plus": None,
    "Приобретение отзывов на платформе": None,
    "Удержание за недовложение товара": None,
    "Услуга за обработку операционных ошибок продавца: отмена": None,
    "Услуга за обработку операционных ошибок продавца: просроченная отгрузка": None,
    "Услуга продвижения Бонусы продавца": None,
    "Услуга размещения товаров на складе": None,
    "Утилизация": None,
}


class PriceComponentMatch(models.Model):
    _name = "ozon.price_component_match"
    _description = "Сопоставление фактических статей затрат Ozon с плановыми"

    name = fields.Char(string="Фактическая статья затрат Ozon")
    price_component_id = fields.Many2one("ozon.price_component", string="Плановый компонент цены")

    def refill_model(self):
        self.env["ozon.price_component_match"].search([]).unlink()
        pcm = self.env["ozon.price_component"]
        pcm.fill_model()
        data = []
        for fact, identifier in FACT_PLAN_MATCH.items():
            price_component = pcm.search([("identifier", "=", identifier)])
            data.append({
                "name": fact,
                "price_component_id": price_component.id if price_component else None,
            })
        self.create(data)
    
    def get_fact_plan_match(self):
        return {i.name: i.price_component_id.name if i.price_component_id else "Unknown" 
                for i in self.search([])}