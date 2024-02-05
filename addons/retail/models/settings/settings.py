from odoo import models, fields


class BaseSettings(models.AbstractModel):
    _name = "retail.base.settings"
    _description = 'Базовый класс настроек "Розничной торговли"'

    name = fields.Selection(
        [],
        string="Ключ",
    )
    value = fields.Char(string="Значение")


class Settings(models.Model):
    _name = "retail.settings"
    _description = 'Настройки "Розничной торговли"'
    _inherit = "retail.base.settings"

    name = fields.Selection(
        selection_add=[
            ("API_KEY_1C", "Ключ для импорта .xml файла розничной торговли"),
        ]
    )