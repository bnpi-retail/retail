import json
import ast

from odoo import http
from odoo.http import Response, request


class AnalysysDataLotsController(http.Controller):
    @http.route("/api/v1/save-analysys-data-lots", 
                auth="user", 
                type="http", 
                csrf=False, 
                methods=["POST"])
    def save_analysys_data_lots(self, data, **post):
        data = ast.literal_eval(data)
        
        model_products = http.request.env["ozon.products"]
        model_analysis_data = http.request.env["ozon.analysis_data"]

        for sku, info in data.items():
            product = model_products \
                .search([("id_on_platform", "=", sku)], limit=1)
            
            model_analysis_data.create({
                "product": product.id,
                "hits_view": info["hits_view"],
                "hits_tocart": info["hits_tocart"],
            })

        response_data = {"response": "success", "message": "Processed successfully"}
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )