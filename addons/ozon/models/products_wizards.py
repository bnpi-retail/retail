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
        prod_ids = self._context["active_ids"]
        products = self.env["ozon.products"].browse(prod_ids)
        # data = []
        # for prod in products:
        #     for ps in self.pricing_strategy_ids:
        #         data.append(
        #             {
        #                 "name": ps.name,
        #                 "strategy_id": ps.strategy_id,
        #                 "weight": ps.weight,
        #                 "value": ps.value,
        #                 "product_id": prod.id,
        #             }
        #         )
        # products.pricing_strategy_ids.unlink()
        # self.env["ozon.pricing_strategy"].create(data)
