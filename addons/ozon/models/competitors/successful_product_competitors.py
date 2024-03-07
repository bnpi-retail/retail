from odoo import models, fields, api
from odoo.exceptions import UserError

class SuccessfulProductCompetitors(models.Model):
    _name = 'ozon.successful_product_competitors'
    _description = 'Успешные товары конкурентов'

    name = fields.Char(string="Название товара конкурента")
    sku = fields.Char(string="SKU")
    product = fields.Many2one("ozon.products", string="Наш товар")
    search_query = fields.Char(string="Поисковый запрос")
    is_matched = fields.Boolean(string="Сопоставлен", readonly=True)
    
    def name_get(self):
        result = []
        for record in self:
            display_name = f"{record.sku} - {record.name}"
            result.append((record.id, display_name))
        return result

    def write(self, values):
        if self.is_matched:
            return
        if values.get("product", self.product):
            self.create_competitor_product(values)
            values.update({"is_matched": True})
        rec = super(SuccessfulProductCompetitors, self).write(values)
        return rec
    
    def create_competitor_product(self, values):
        if self.env["ozon.products_competitors"].search([("id_product", "=", self.sku)]):
            return
        sku = values.get("sku", self.sku)
        name = values.get("name", self.name)
        product = values.get("product", self.product)
        data = {"id_product": sku, "name": name, "product": product}
        comp_product = self.env["ozon.products_competitors"].create(data)
        if self.search_query:
            search_query = values.get("search_query", self.search_query)
            comp_product.tracked_search_query_ids = [(0, 0, {"name": search_query})]