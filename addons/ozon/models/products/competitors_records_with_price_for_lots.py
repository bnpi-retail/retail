from odoo import models, fields, api


class CompetitorsRecordsWithPriceForLots(models.Model):
    _name = "ozon.competitors_records_with_price_for_lots"
    _description = "Записи конкурентов с актуальной ценой для модели 'Лоты'"

    product_id = fields.Many2one('ozon.products', string='Наш товар')
    competitor_record_id = fields.Many2one(
        "ozon.products_competitors", 
        string="Товар конкурента",
    )
    actually_price = fields.Float(string="Актуальная цена")

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, record.product.products.name))
        return result
