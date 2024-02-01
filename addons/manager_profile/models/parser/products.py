from odoo import models, fields, api


class ProductCompetitors(models.Model):
    _name = "parser.products_competitors"
    _description = "Товары конкуренты"

    id_product = fields.Char(string="Id товара на Ozon")
    article = fields.Char(string="Артикул", unique=True)
    
    name = fields.Char(string="Наименование товара")

    retail_seller_id = fields.Many2one('retail.seller', string="Продавец")

    url = fields.Char(
        string="URL товара", widget="url", help="Укажите ссылку на товар в поле"
    )

    product = fields.Many2one("ozon.products", string="Лот")

    price_competitors_count = fields.One2many(
        "ozon.price_history_competitors",
        "product_competitors",
        string="Количество цен товара конкурента",
    )
    get_price_competitors_count = fields.Integer(
        compute="compute_count_price_competitors"
    )


class NameGet(models.Model):
    _inherit = "parser.products_competitors"

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result

