import json
import ast

from odoo import http
from odoo.http import Response


class LotsForGPTController(http.Controller):
    @http.route("/api/v1/get-all-skus-of-lots", 
                auth="user", 
                csrf=False,
                methods=["GET"])
    def get_all_skus_of_lots(self, **kwargs):
        model_ozon_products = http.request.env["ozon.products"]
        records = model_ozon_products.search([])
        product_competitors = records.mapped("id_on_platform")
        json_response = json.dumps(product_competitors)
        return http.Response(json_response, content_type="application/json")

    @http.route("/api/v1/save-numbers-of-products-history", 
                auth="user", 
                type="http", 
                csrf=False, 
                methods=["POST"])
    def save_numbers_of_products_history(self, data, **post):
        data = ast.literal_eval(data)
        
        model_products = http.request.env["ozon.products"]
        model_stock = http.request.env["ozon.stock"]

        for sku, info in data.items():
            product = model_products \
                .search([("id_on_platform", "=", sku)], limit=1)
            
            model_stock.create({
                "product": product.id,
                "stocks_fbs": info["present"],
                "stocks_reserved_fbs": info["reserved"],
            })

        response_data = {"response": "success", "message": "Processed successfully"}
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )