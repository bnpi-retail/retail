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
