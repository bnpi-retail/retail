from odoo import models, fields, api


class BaseCalculation(models.Model):
    _name = "ozon.base_calculation"
    _description = "План (Базовый расчёт)"

    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    price_component_id = fields.Many2one("ozon.price_component", string="Компонент цены")
    kind = fields.Selection([
            ("percent", "Процент от цены"),
            ("fix", "Число"),
            ("depends_on_volume", "Зависит от объёма"),
        ], string="Тип начисления")
    value = fields.Float(string="Значение")