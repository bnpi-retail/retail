from odoo import models, fields, api


class ParserProductCompetitors(models.Model):
    _name = "parser.products_competitors"
    _description = "Товары конкуренты"

    product = fields.Many2one("ozon.products", string="Рекомендуемый наш товар")
    is_our_product = fields.Boolean(string="Наш товар")

    number = fields.Char(string="Номер позиции карточки Ozon")
    name = fields.Char(string="Наименование товара")
    search_query = fields.Char(string="Поисковый запрос")
    seller = fields.Char(string="Продавец")
    id_product = fields.Char(string="Product ID")
    price = fields.Float(string="Цена товара")
    price_without_sale = fields.Float(string="Цена товара без скидки")
    price_with_card = fields.Float(string="Цена товара по карте Ozon")
    url = fields.Char(
        string="URL товара", widget="url", help="Укажите ссылку на товар в поле"
    )

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result

