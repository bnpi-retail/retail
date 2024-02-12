import json
from odoo import http
from odoo.http import Response


class ParserPlugin(http.Controller):
    @http.route('/update_seacrh_query_products', auth='user', type='http', csrf=False, methods=["GET"])
    def parser_plugin(self, **kwargs):
        model_products_competitors = http.request.env["parser.products_competitors"]

        records = model_products_competitors.search([])
        
        for record in records:

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

            self.get_or_create_product_competitors(
                record=record,
                record_search_query_parser=record_search_query_parser
            )

        return Response(
            response=json.dumps({'response': 'success'}),
            status=200,
            content_type='application/json'
        )
    
    def get_or_create_product_competitors(self, record, record_search_query_parser):
        model_products_competitors = http.request.env["ozon.products_competitors"]
    
        record_product_competitors = model_products_competitors \
            .search([("id_product", "=", record.id_product)], limit=1)

        if not record_product_competitors:
            record_product_competitors = model_products_competitors \
                .create({
                    "id_product": record.id_product,
                    "search_query": record_search_query_parser.id,
                })
                
        record_product_competitors \
            .write({
                "article": record.product.article,
                "product": record.product.id,
                "name": record.name,
                "url": record.url,
                "search_query": record_search_query_parser.id,
            })

        return record_product_competitors

    def get_or_create_search_query_record(self, record):
        model_search_queries_parser = http.request.env["ozon.search_queries_parser"]

        record_search_queries_parser = model_search_queries_parser \
            .search([("search_query", "=", record.search_query)], limit=1)

        if not record_search_queries_parser:
            record_search_queries_parser = model_search_queries_parser \
                .create({
                    "search_query": record.search_query,
                })
        
        return record_search_queries_parser

    def append_search_query_to_product(self, record, record_search_query_parser) -> None:
        model_products = http.request.env["ozon.products"]

        record = model_products.search([("sku", "=", record.id_product)])

        if not record:
            record = model_products.search([("fbo_sku", "=", record.id_product)])
        
        if not record:
            record = model_products.search([("fbs_sku", "=", record.id_product)])

        record.write({
            "search_query": record_search_query_parser.id
        })

    def create_history_of_products_position_record(self, record, record_search_query_parser):
        model_history_of_product_positions = http.request.env["ozon.history_of_product_positions"]
        model_history_of_product_positions.create({
            "number": record.number,
            "id_product": record.id_product,
            "search_query": record_search_query_parser.id,
        })

