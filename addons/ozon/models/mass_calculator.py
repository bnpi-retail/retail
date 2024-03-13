from odoo import models, fields, api

class MassCalculator(models.Model):
    _name = "ozon.mass_calculator"
    _description = "Массовый калькулятор"

    category_id = fields.Many2one("ozon.categories", string="Категория товаров")
    draft_product_ids = fields.One2many("ozon.draft_product", "mass_calculator_id", 
                                        string="Товары-черновики")