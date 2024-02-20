from odoo import models, fields, api

from .price_component import BASE_CALCULATION_COMPONENTS

class BaseCalculation(models.Model):
    _name = "ozon.base_calculation"
    _description = "План (Базовый расчёт)"

    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    price_component_id = fields.Many2one("ozon.price_component", string="Компонент цены")
    kind = fields.Selection([
            ("percent", "Процент от цены"),
            ("percent_cost_price", "Процент от себестоимости"),
            ("fix", "Значение, ₽"),
            ("depends_on_volume", "Значение, ₽ (зависит от объёма)"),
        ], string="Тип начисления")
    value = fields.Float(string="Значение")

    def reset_for_product(self, product):
        product.base_calculation_ids.unlink()
        data = []
        p_id = product.id
        for pc in self.env["ozon.price_component"].search([]).filtered(
            lambda r: r.identifier in BASE_CALCULATION_COMPONENTS):
            if pc.identifier == "logistics":
                value = product.all_expenses_ids.filtered(lambda r: r.category == "Логистика").value
                kind = "depends_on_volume"
            elif pc.identifier == "last_mile":
                value = product.all_expenses_ids.filtered(
                    lambda r: r.category == "Последняя миля").percent * 100
                kind = "percent"
            elif pc.identifier == "acquiring":
                value = product.all_expenses_ids.filtered(lambda r: r.category == "Эквайринг").percent * 100
                kind = "percent"
            elif pc.identifier == "ozon_reward":
                value = product.all_expenses_ids.filtered(
                    lambda r: r.category == "Вознаграждение Ozon").percent * 100
                kind = "percent"
            elif pc.identifier == "promo":
                value = 10
                kind = "percent"
            elif pc.identifier == "tax":
                value = product.all_expenses_ids.filtered(lambda r: r.name == "Налог").percent * 100
                kind = "percent"
            elif pc.identifier == "processing":  
                value = product.all_expenses_ids.filtered(lambda r: r.category == "Обработка").value
                kind = "fix"
            elif pc.identifier == "company_processing_and_storage": 
                value = 100
                kind = "fix"
            elif pc.identifier == "company_packaging": 
                value = 20
                kind = "fix"
            elif pc.identifier == "company_marketing": 
                value = 50
                kind = "fix"
            elif pc.identifier == "company_operators": 
                value = 20
                kind = "fix"
            elif pc.identifier == "roe": 
                value = 0
                kind = "percent_cost_price"
            else:
                value = 0
                kind = "fix"
            data.append({"product_id": p_id, "price_component_id": pc.id, "value": value, "kind": kind})
        self.create(data)

    def fill_if_not_exists(self, product):
        if product.base_calculation_ids:
            return
        self.reset_for_product(product)