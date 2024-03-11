from odoo import models, fields, api

class DraftProduct(models.Model):
    _name = "ozon.draft_product"
    _description = "Товар-черновик"

    name = fields.Char(string="Название")
    cost_price = fields.Float(string="Себестоимость")
    category_id = fields.Many2one("ozon.categories", string="Категория Ozon")
    base_calculation_ids = fields.One2many ("ozon.base_calculation", "draft_product_id", 
                                            string="Плановый расчёт")
