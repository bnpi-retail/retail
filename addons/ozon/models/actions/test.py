from odoo import api, fields, models

class Test(models.Model):
    _name = 'ozon.test'

    @api.model
    def test_button(self):
        # Пустая функция, не выполняющая никаких действий
        pass
