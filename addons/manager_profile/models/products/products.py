from odoo import models, fields, api


class ParserProductCompetitors(models.Model):
    _name = "parser.products_competitors"
    _description = "Товары конкуренты"

    is_processed = fields.Selection(
        [
            ("complete", "Товар обработан"),
            ("not_complete", "Товар ждет обработки"),
            ("product_not_assigned", "Наш товар не назначен")
        ],
        string="Статус",
        compute='_compute_is_processed',
        readonly=True,
        store=True,
    )
    is_processed_finish = fields.Boolean(string="Обработан ли товар", default=False)

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

    @api.depends('product', 'is_processed_finish')
    def _compute_is_processed(self):
        for record in self:
            if record.is_processed_finish is True:
                record.is_processed = 'complete'
            elif record.product:
                record.is_processed = 'not_complete'
            else:
                record.is_processed = 'product_not_assigned'


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
            if record.is_processed == "complete" \
            or record.is_processed == "product_not_assigned":
                continue

            record.is_processed_finish = "complete"

            record_search_query_parser = self.get_or_create_search_query_record(
                record=record,
            )

            self.create_history_of_products_position_record(
                record=record,
                record_search_query_parser=record_search_query_parser,
            )

            if record.is_our_product is True:
                self.append_search_query_to_product(
                    record=record,
                    record_search_query_parser=record_search_query_parser
                )
                continue

            record_seller = self.get_or_create_seller(
                record=record,
            )

            record_product_competitors = self.get_or_create_product_competitors(
                record=record,
                record_seller=record_seller,
                record_search_query_parser=record_search_query_parser
            )
            self.create_price_history_competitors(
                record=record,
                record_product_competitors=record_product_competitors,
            )

    def get_or_create_seller(self, record):
        model_competitor_seller = self.env["ozon.competitor_seller"]

        record_seller = model_competitor_seller \
            .search([("trade_name", "=", record.seller)], limit=1)

        if not record_seller:
            record_seller = model_competitor_seller \
                .create({
                    "trade_name": record.seller,
                })
            
        return record_seller
    
    def get_or_create_product_competitors(self, record, record_seller, record_search_query_parser):
        model_products_competitors = self.env["ozon.products_competitors"]
    
        record_product_competitors = model_products_competitors \
            .search([("id_product", "=", record.id_product)], limit=1)

        if not record_product_competitors:
            record_product_competitors = model_products_competitors \
                .create({
                    "id_product": record.id_product,
                })
        if record_search_query_parser.id not in record_product_competitors.tracked_search_query_ids.ids:
            record_product_competitors \
                .write({
                    'tracked_search_query_ids': [(4, record_search_query_parser.id)]
                })

        record_product_competitors \
            .write({
                "article": record.product.article,
                "product": record.product.id,
                "name": record.name,
                "url": record.url,
                "competitor_seller_id": record_seller.id,
            })

        return record_product_competitors

    def get_or_create_search_query_record(self, record):
        model_search_queries_parser = self.env["ozon.tracked_search_queries"]

        record_search_queries_parser = model_search_queries_parser \
            .search([("name", "=", record.search_query)], limit=1)

        if not record_search_queries_parser:
            record_search_queries_parser = model_search_queries_parser \
                .create({
                    "name": record.search_query,
                })
        
        return record_search_queries_parser

    def append_search_query_to_product(self, record, record_search_query_parser) -> None:
        model_products = self.env["ozon.products"]

        product_record = model_products.search([("sku", "=", record.id_product)])

        if not product_record:
            product_record = model_products.search([("fbo_sku", "=", record.id_product)])
        
        if not product_record:
            product_record = model_products.search([("fbs_sku", "=", record.id_product)])

        existing_record = product_record.tracked_search_query_ids.filtered(
            lambda x: x.id == record_search_query_parser.id
        )

        if not existing_record:
            product_record.write({
                'tracked_search_query_ids': [(4, record_search_query_parser.id)]
            })

    def create_history_of_products_position_record(self, record, record_search_query_parser):
        model_history_of_product_positions = self.env["ozon.history_of_product_positions"]
        model_history_of_product_positions \
            .create({
                "number": record.number,
                "id_product": record.id_product,
                "search_query": record_search_query_parser.id,
            })

    def create_price_history_competitors(self, record, record_product_competitors):
        model_price_history_competitors = self.env["ozon.price_history_competitors"]
        model_price_history_competitors \
            .create({
                "price": record.price,
                "price_with_card": record.price_with_card,
                "price_without_sale": record.price_without_sale,
                "product_competitors": record_product_competitors.id,
            })
        
    def create_tracked_search_query_record(self, target_record, record_search_query_parser, model):
        model_tracked_search_queries = self.env["ozon.tracked_search_queries"]
    
        tracked_search_record = model_tracked_search_queries \
            .create({
                    "search_query": record_search_query_parser.id,
                })

        return tracked_search_record