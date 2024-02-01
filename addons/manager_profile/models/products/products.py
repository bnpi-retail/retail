from email.policy import default
from odoo import models, fields, api


class ParserProductCompetitors(models.Model):
    _name = "parser.products_competitors"
    _description = "Товары конкуренты"

    is_processed = fields.Selection([
        ("complete", "Товар назначен"),
        ("not_complete", "Ждет назначения товара")],
        string="Статус",
        readonly=True,
        default="not_complete",
    )

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


class NameGetMethod(models.Model):
    _inherit = "parser.products_competitors"

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result


class ActionCreateOzonProducts(models.Model):
    _inherit = "parser.products_competitors"

    def create_ozon_product(self):
        for record in self:
            if not record.product \
            or record.is_our_product is True \
            or record.is_processed is "complete":
                continue
                
            record.is_processed = "complete"

            record_seller = self.get_or_create_seller(
                record=record,
            )
            record_product_competitors = self.get_or_create_product_competitors(
                record=record,
                record_seller=record_seller,
            )
            self.create_price_history_competitors(
                record=record,
                record_product_competitors=record_product_competitors,
            )

    def get_or_create_seller(self, record):
        model_seller = self.env["retail.seller"]

        record_seller = model_seller \
            .search([("name", "=", record.seller)])

        if not record_seller:
            record_seller = model_seller \
                .create({
                    "name": record.name,
                })
            
        return record_seller
    
    def get_or_create_product_competitors(self, record, record_seller):
        model_products_competitors = self.env["ozon.products_competitors"]
    
        record_product_competitors = model_products_competitors \
            .search([("id_product", "=", record.id_product)])

        if not record_product_competitors:
            record_product_competitors = model_products_competitors \
                .create({
                    "id_product": record.id_product,
                })
                
        record_product_competitors.write({
            "article": record.product.article,
            "product": record.product.id,
            "name": record.name,
            "url": record.url,
            "retail_seller_id": record_seller.id,
        })

        return record_product_competitors

    def create_price_history_competitors(self, record, record_product_competitors):
        model_price_history_competitors = self.env["ozon.price_history_competitors"]

        model_price_history_competitors.create({
                # "product_competitors": record_product_competitors.id,
                "price": record.price,
                "price_with_card": record.price_with_card,
                "price_without_sale": record.price_without_sale,
            })
