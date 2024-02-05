from odoo import models, fields, api


class BaseSettings(models.AbstractModel):
    _name = "ozon.base.settings"
    _description = 'Базовый класс настроек'

    name = fields.Selection(
        [],
        string="Ключ",
    )
    value = fields.Char(string="Значение")


class Settings(models.Model):
    _name = "ozon.settings"
    _description = "Настройки Ozon"
    _inherit = "ozon.base.settings"

    name = fields.Selection(
        [
            ("OZON_API_KEY", "Ozon API-ключ"),
            ("MP_STATS_TOKEN", "MPStats токен"),
            ("API_KEY_1C", "Ключ для импорта файла розничной торговли"),
        ],
        string="Ключ",
    )
