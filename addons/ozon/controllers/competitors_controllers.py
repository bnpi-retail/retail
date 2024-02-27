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
        print(response_data)
        
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

        created_qty = 0
        vals_to_create = []
        for ad in ads:
            if ad['no_data'] == 1:
                continue
            
            product_competitors = model_products_competitors.search(
                [("id_product", "=", sku)],
                limit=1,
            )
            values = {
                'product_competitors': product_competitors.id,
                'balance': ad['balance'],
                'sales': ad['sales'],
                'price_without_sale': ad['price'],
                'price': ad['final_price'],
                'comments': ad['comments'],
                'rating': ad['rating'],
            }
            if ad.get('ozon_card_price'):
                values['price_with_card'] = ad.get('ozon_card_price')
            vals_to_create.append(values)
            created_qty += 1

        model_price_history_competitors.create(vals_to_create)

        log_data = {'Добавлено историй цен конкурентов': created_qty}
        json_response = json.dumps(log_data)
        return json_response
