from odoo import models, fields, api


class SuccessfulProductCompetitors(models.Model):
    _name = 'ozon.successful_product_competitors'
    _description = 'Успешные товары конкурентов'

    name = fields.Char(string='Наименование')
    sku = fields.Char(string='SKU')
    product = fields.Many2one("ozon.products", string="Наш товар")
    
    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            display_name = f"{record.sku} - {record.name}"
            result.append((record.id, display_name))
        return result
