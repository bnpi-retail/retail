from odoo import models, fields, api


class MassPricing(models.Model):
    _name = "ozon.mass_pricing"
    _description = "Массовое назначение цен"

    status = fields.Selection(
        [
            ("created", "Создано"),
            ("applied", "Применено"),
        ],
        string="Статус",
    )
    product = fields.Many2one("ozon.products", string="Товар Ozon")
    new_price = fields.Float(string="Новая цена")
    comment = fields.Text(string="Причина")
