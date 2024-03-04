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

class PriceComponentMatch(models.Model):
    _name = "ozon.price_component_match"
    _description = "Сопоставление фактических статей затрат с плановыми"

    name = fields.Char(string="Фактическая статья затрат")
    price_component_id = fields.Many2one("ozon.price_component", string="Плановый компонент цены")