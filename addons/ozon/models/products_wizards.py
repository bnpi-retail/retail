# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductsMassPricingWizard(models.TransientModel):
    _name = "ozon.products_mass_pricing.wizard"
    _description = "Wizard Массовое назначение стратегий"

    pricing_strategy_ids = fields.Many2many(
        "ozon.pricing_strategy", string="Стратегии назначения цен"
    )

    def assign_calculated_pricing_strategy_ids(self):
        """Массово назначает calculated_pricing_strategy_ids исходя из выбранных стратегий для выбранных товаров"""
        prod_ids = self._context["active_ids"]
        products = self.env["ozon.products"].browse(prod_ids)
        data = []
        today = fields.Date.today()
        for prod in products:
            for ps in self.pricing_strategy_ids:
                data.append(
                    {
                        "pricing_strategy_id": ps.id,
                        "timestamp": today,
                        "weight": ps.weight,
                        "value": ps.value,
                        "product_id": prod.id,
                    }
                )
        products.calculated_pricing_strategy_ids.unlink()
        self.env["ozon.calculated_pricing_strategy"].create(data)
        for prod in products:
            prod.calculate_calculated_pricing_strategy_ids()


class ProductsAvgValueToUseMassWizard(models.TransientModel):
    _name = "ozon.products.avg_value_to_use.assign"
    _description = "Wizard массового назначение avg_value_to_use"

    avg_value_to_use = fields.Selection(
        [
            ('input', 'Использовать значения, введённые вручную'),
            ('category', 'Использовать значения по категории'),
            ('report', 'Использовать значения по магазину из последнего отчёта о выплатах'),
        ],
        default='input',
        string="Значения для расчета фактических статей затрат",
    )

    def assign_avg_value_to_use(self):
        products = self.env["ozon.products"].browse(self._context["active_ids"])
        products.write({"avg_value_to_use": self.avg_value_to_use})