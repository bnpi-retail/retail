from odoo import models, fields, api


class PriceComponent(models.Model):
    _name = "ozon.price_component"
    _description = "Компонент цены"

    name = fields.Char(string="Название")


    def get_or_create(self, name):
        component = self.search([("name", "=", name)])
        if not component:
            component = self.create({"name": name})
        return component