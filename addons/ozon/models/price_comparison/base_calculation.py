from odoo import models, fields, api

from .price_component import (BASE_CALCULATION_COMPONENTS, 
                              PERCENT_COMPONENTS, 
                              PERCENT_COST_PRICE_COMPONENTS, 
                              DEPENDS_ON_VOLUME_COMPONENTS)

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
        ], string="Тип начисления", compute="_compute_kind")
    value = fields.Float(string="Значение")

    def _compute_kind(self):
        for r in self:
            if r.price_component_id.identifier in PERCENT_COMPONENTS:
                r.kind = "percent"
            elif r.price_component_id.identifier in PERCENT_COST_PRICE_COMPONENTS:
                r.kind = "percent_cost_price"
            elif r.price_component_id.identifier in DEPENDS_ON_VOLUME_COMPONENTS:
                r.kind = "depends_on_volume"
            else:
                r.kind = "fix"

    def _base_calculation_components(self):
        return self.env["ozon.price_component"].search([]).filtered(
            lambda r: r.identifier in BASE_CALCULATION_COMPONENTS)

    def create_base_calculation_components(self):
        data = []
        for pc in self._base_calculation_components():
            data.append({"price_component_id": pc.id})
        return self.create(data)

    def reset_for_products(self, products):
        products.base_calculation_ids.unlink()
        data = []
        for product in products:
            p_id = product.id
            for pc in self._base_calculation_components():
                if pc.identifier == "logistics":
                    value = product.all_expenses_ids.filtered(lambda r: r.category == "Логистика").value
                elif pc.identifier == "last_mile":
                    value = product.all_expenses_ids.filtered(
                        lambda r: r.category == "Последняя миля").percent * 100
                elif pc.identifier == "acquiring":
                    value = product.all_expenses_ids.filtered(lambda r: r.category == "Эквайринг").percent * 100
                elif pc.identifier == "ozon_reward":
                    value = product.all_expenses_ids.filtered(
                        lambda r: r.category == "Вознаграждение Ozon").percent * 100
                elif pc.identifier == "promo":
                    value = 10
                elif pc.identifier == "tax":
                    value = product.all_expenses_ids.filtered(lambda r: r.name == "Налог").percent * 100
                elif pc.identifier == "processing":  
                    value = product.all_expenses_ids.filtered(lambda r: r.category == "Обработка").value
                elif pc.identifier == "company_processing_and_storage": 
                    value = 100
                elif pc.identifier == "company_packaging": 
                    value = 20
                elif pc.identifier == "company_marketing": 
                    value = 50
                elif pc.identifier == "company_operators": 
                    value = 20
                elif pc.identifier == "roe": 
                    value = 0
                else:
                    value = 0
                data.append({"product_id": p_id, "price_component_id": pc.id, "value": value})
        self.create(data)

    def fill_if_not_exists(self, product):
        if product.base_calculation_ids:
            return
        self.reset_for_products(product)  

class BaseCalculationTemplate(models.Model):
    _name = "ozon.base_calculation_template"
    _description = "Шаблон планового расчёта"

    name = fields.Char(string="Название")
    base_calculation_ids = fields.Many2many("ozon.base_calculation", string="Плановый расчёт")

    def create_if_not_exists(self):
        if not self.search([]):
            bc_comps = self.env["ozon.base_calculation"].create_base_calculation_components()
            self.create({"name": "Шаблон", "base_calculation_ids": bc_comps})

class BaseCalculationWizard(models.Model):
    _name = "ozon.base_calculation_wizard"
    _description = "Wizard - Шаблон планового расчёта"

    base_calculation_template_id = fields.Many2one("ozon.base_calculation_template", 
                                                   string="Шаблон планового расчёта")

    def apply_to_products(self):
        """Applies base_calculation_template to products"""
        products = self.env["ozon.products"].browse(self._context["active_ids"])
        data = []
        products.base_calculation_ids.unlink()
        template = self.base_calculation_template_id
        for prod in products:
            p_id = prod.id
            for r in template.base_calculation_ids: 
                data.append({"product_id": p_id, 
                             "price_component_id": r.price_component_id.id,
                             "value": r.value})
        self.env["ozon.base_calculation"].create(data)



class LogisticsTariff(models.Model):
    _name = "ozon.logistics_tariff"
    _description = "Тариф логистики"

    name = fields.Selection([
        ("1", "От 0,1 до 5 литров включительно — 76 рублей"),
        ("2", "До 175 литров включительно — 9 рублей за каждый дополнительный литр свыше объёма 5 л"),
        ("3", "Свыше 175 литров — 1615 рублей")],
        string="Тариф")

    def name_get(self):
        result = []
        for r in self:
            result.append((r.id, f"""{dict(self._fields['name'].selection).get(r.name)}"""))
        return result


        