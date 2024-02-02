# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductsMassPricingWizard(models.TransientModel):
    _name = "ozon.products_mass_pricing.wizard"
    _description = "Wizard Массовое назначение стратегий"

    pricing_strategy_ids = fields.Many2many(
        "ozon.pricing_strategy", string="Стратегии назначения цен"
    )

    def change_calculated_price_based_on_all_strategies(self):
        """Массово назначает рассчитанную цену исходя из выбранных стратегий для выбранных товаров"""
        # TODO
        print("here")
        pass
        # prod_ids = self._context["active_ids"]
        # products = self.env["ozon.products"].browse(prod_ids)
        # products.write({"profitability_norm": self.profitability_norm})
