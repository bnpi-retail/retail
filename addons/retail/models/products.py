import uuid

from datetime import datetime, time, timedelta
from odoo import models, fields, api, exceptions


class Product(models.Model):
    _name = "retail.products"
    _description = "Продукты"

    name = fields.Char(string="Наименование товара")
    description = fields.Text(string="Описание товара")
    keywords = fields.Text(string="Ключевые слова")
    product_id = fields.Char(string="Артикул", unique=True, readonly=True)

    length = fields.Float(string="Длина, дм")
    width = fields.Float(string="Ширина, дм")
    height = fields.Float(string="Высота, дм")
    weight = fields.Float(string="Вес, кг")
    volume = fields.Float(string="Объем, л", compute="_compute_volume", store=True)

    def get_cost_price(self):
        self.ensure_one()

        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90) 

        return {
            'type': 'ir.actions.act_window',
            'name': 'История себестоимости',
            'view_mode': 'tree,graph',
            'res_model': 'retail.cost_price',
            'domain': [
                ('products', '=', self.id),
                ('timestamp', '>=', three_months_ago.strftime('%Y-%m-%d %H:%M:%S'))
            ],
            'context': {
                'create': False,
                'views': [(False, 'tree'), (False, 'form'), (False, 'graph')],
                'search_default_name': "[('volume','=',1)]",
            }
        }

    @api.depends("length", "width", "height")
    def _compute_volume(self):
        for record in self:
            record.volume = record.length * record.width * record.height

    @api.model
    def create(self, values):
        existing_record = self.search(
            [("product_id", "=", values.get("product_id"))], limit=1
        )
        if existing_record:
            return existing_record

        values["volume"] = values["length"] * values["width"] * values["height"]
        return super(Product, self).create(values)
