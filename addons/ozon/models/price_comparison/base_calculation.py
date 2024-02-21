from math import ceil

from odoo import models, fields, api

from .price_component import (BASE_CALCULATION_COMPONENTS, 
                              PERCENT_COMPONENTS, 
                              PERCENT_COST_PRICE_COMPONENTS, 
                              DEPENDS_ON_VOLUME_COMPONENTS)

class BaseCalculation(models.Model):
    _name = "ozon.base_calculation"
    _description = "Плановый расчёт"

    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    price_component_id = fields.Many2one("ozon.price_component", string="Компонент цены")
    kind = fields.Selection([
            ("percent", "Процент от цены"),
            ("percent_cost_price", "Процент от себестоимости"),
            ("fix", "Значение, ₽"),
            ("depends_on_volume", "Значение, ₽ (зависит от объёма)"),
        ], string="Тип начисления", compute="_compute_kind")
    value = fields.Float(string="Значение")
    comment = fields.Text(string="Комментарий")

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
            if pc.identifier == "logistics":
                data.append({"price_component_id": pc.id, "comment": "В зависимости от тарифа логистики"})
            else:
                data.append({"price_component_id": pc.id})
        return self.create(data)

    def reset_for_products(self, products):
        products.base_calculation_ids.unlink()
        data = []
        for product in products:
            p_id = product.id
            for pc in self._base_calculation_components():
                data.append({"product_id": p_id, "price_component_id": pc.id, "value": 0})
                # if pc.identifier == "logistics":
                #     value = product.all_expenses_ids.filtered(lambda r: r.category == "Логистика").value
                # elif pc.identifier == "last_mile":
                #     value = product.all_expenses_ids.filtered(
                #         lambda r: r.category == "Последняя миля").percent * 100
                # elif pc.identifier == "acquiring":
                #     value = product.all_expenses_ids.filtered(lambda r: r.category == "Эквайринг").percent * 100
                # elif pc.identifier == "ozon_reward":
                #     value = product.all_expenses_ids.filtered(
                #         lambda r: r.category == "Вознаграждение Ozon").percent * 100
                # elif pc.identifier == "promo":
                #     value = 10
                # elif pc.identifier == "tax":
                #     value = product.all_expenses_ids.filtered(lambda r: r.name == "Налог").percent * 100
                # elif pc.identifier == "processing":  
                #     value = product.all_expenses_ids.filtered(lambda r: r.category == "Обработка").value
                # elif pc.identifier == "company_processing_and_storage": 
                #     value = 100
                # elif pc.identifier == "company_packaging": 
                #     value = 20
                # elif pc.identifier == "company_marketing": 
                #     value = 50
                # elif pc.identifier == "company_operators": 
                #     value = 20
                # elif pc.identifier == "roe": 
                #     value = 0
                # else:
                #     value = 0
                # data.append({"product_id": p_id, "price_component_id": pc.id, "value": value})
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
        log_tar_model = self.env["ozon.logistics_tariff"]
        for prod in products:
            p_id = prod.id
            for r in template.base_calculation_ids:
                if r.price_component_id.identifier == "logistics":
                    if not prod.logistics_tariff_id:
                        log_tar_model.assign_logistics_tariff_id(prod)
                    log_value = log_tar_model.get_logistics_cost_based_on_tariff(prod)
                    data.append({"product_id": p_id, 
                                 "price_component_id": r.price_component_id.id, 
                                 "value": log_value,
                                 "comment": f"Объём: {round(prod.products.volume, 2)}л\n"
                                 f"Тариф: {prod.logistics_tariff_id.name}"})
                else:
                    data.append({"product_id": p_id, 
                                "price_component_id": r.price_component_id.id,
                                "value": r.value})
        self.env["ozon.base_calculation"].create(data)



class LogisticsTariff(models.Model):
    _name = "ozon.logistics_tariff"
    _description = "Тариф логистики"

    name = fields.Char(string="Тариф")
    identifier = fields.Integer(string="Идентификатор")

    def create_if_not_exists(self):
        if len(self.search([])) < 3:
            self.create([
                {"name": "От 0,1 до 5 литров включительно — 76 рублей", "identifier": 1},
                {"name": "До 175 литров включительно — 9 рублей за каждый дополнительный литр свыше объёма 5 л",
                 "identifier": 2},
                {"name": "Свыше 175 литров — 1615 рублей", "identifier": 3}
            ])
            self.unlink()
            return {
                "type": "ir.actions.act_window",
                "name": "Тарифы логистики",
                "view_mode": "tree,form",
                "res_model": "ozon.logistics_tariff",
            }
    
    def assign_logistics_tariff_id(self, products):
        tariff_1_id = self.search([("identifier", "=", 1)]).id
        tariff_2_id = self.search([("identifier", "=", 2)]).id
        tariff_3_id = self.search([("identifier", "=", 3)]).id
        for prod in products:
            if prod.logistics_tariff_id:
                continue
            vol = prod.products.volume
            if vol <= 5:
                prod.logistics_tariff_id = tariff_1_id
            elif 5 < vol <= 175:
                prod.logistics_tariff_id = tariff_2_id
            else:
                prod.logistics_tariff_id = tariff_3_id

    def get_logistics_cost_based_on_tariff(self, product):
        if not product.logistics_tariff_id:
            return "Logistics tariff is not assigned to the product"
        if product.logistics_tariff_id.identifier == 1:
            return 76
        elif product.logistics_tariff_id.identifier == 2:
            vol = product.products.volume
            log_cost = 76 + ceil(vol - 5) * 9
            return log_cost
        else:
            return 1615