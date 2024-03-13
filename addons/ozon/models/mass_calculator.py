from odoo import models, fields, api

class MassCalculator(models.Model):
    _name = "ozon.mass_calculator"
    _description = "Массовый калькулятор"

    category_id = fields.Many2one("ozon.categories", string="Категория товаров")
    draft_product_ids = fields.One2many("ozon.draft_product", "mass_calculator_id", 
                                        string="Товары-черновики")
    
    def open_mass_calculator(self):
        view = self.env["ir.ui.view"].search([]).filtered(
            lambda r: r.xml_id == "ozon.ozon_draft_product_in_mass_calculator_tree")
        return {
            "type": "ir.actions.act_window",
            "name": "Калькулятор",
            "view_mode": "tree,form",
            "res_model": "ozon.draft_product",
            "domain": [("mass_calculator_id", "=", self.id)],
            "views": [[view.id, "tree"], [False, "form"]],
        }