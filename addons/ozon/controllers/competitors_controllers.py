import json
import os
import ast

from odoo import http


class CompetitorsGetSKUs(http.Controller):
    @http.route("/api/v1/price_history_competitors/count_records/", type="http", auth="public")
    def get_competitors_count_record(self) -> int:
        total_records = http.request.env["ozon.products_competitors"] \
            .search_count([])
        response_data = {'total_records': total_records}
        json_response = json.dumps(response_data)
        return http.Response(json_response, content_type='application/json')
    
    @http.route("/api/v1/price_history_competitors/get_sku/", type="http", auth="public", methods=["POST"], csrf=False)
    def get_sku_competitors(self, range=None, **post):
        if not range:
            return "Miss required parametr 'range'"

        range_value = int(range)
        records = http.request.env["ozon.products_competitors"].search([], limit=range_value)
        product_competitors = records.mapped('id_product')
        
        response_data = {'product_competitors': product_competitors}
        json_response = json.dumps(response_data)
        return http.Response(json_response, content_type='application/json')

    @http.route("/api/v1/price_history_competitors/create_ads/", type="http", auth="public", methods=["POST"], csrf=False)
    def create_ads_competitors(self, ads=None, sku=None, **post):
        if not ads or not sku:
            return "Miss required parametr 'ads' or 'sku'"

        model_products_competitors = http.request.env["ozon.products_competitors"]
        model_price_history_competitors = http.request.env["ozon.price_history_competitors"]

        ads = ast.literal_eval(ads)
        print(ads)

        for ad in ads:
            if ad['no_data'] == 1:
                continue
            
            result = model_products_competitors.search(
                [("id_product", "=", sku)],
                limit=1,
            )
            model_price_history_competitors.create({
                'product_competitors': result.id,
                'balance': ad['balance'],
                'sales': ad['sales'],
                'price': ad['price'],
                'final_price': ad['final_price'],
            })

        json_response = {'answer': 'success!'}
        return http.Response(json_response, content_type='application/json')