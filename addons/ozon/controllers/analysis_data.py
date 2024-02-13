import json
import ast

from odoo import http
from odoo.http import Response, request
from datetime import datetime


class AnalysysDataLotsController(http.Controller):
    @http.route("/api/v1/save-analysys-data-lots", 
                auth="user", 
                type="http", 
                csrf=False, 
                methods=["POST"])
    def save_analysys_data_lots(self, data, today, one_week_ago, **post):
        data = ast.literal_eval(data)
        today = datetime.strptime(today, "%Y-%m-%d").date()
        one_week_ago = datetime.strptime(one_week_ago, "%Y-%m-%d").date()

        model_products = http.request.env["ozon.products"]
        model_analysis_data = http.request.env["ozon.analysis_data"]

        model_analysis_data_values = []
        for sku, info in data.items():
            product = model_products.search(
                ['|', '|', ("sku", "=", sku), ('fbo_sku', '=', sku), ('fbs_sku', '=', sku)]
                , limit=1
            )

            model_analysis_data_values.append({
                "timestamp_from": today,
                "timestamp_to": one_week_ago,
                "product": product.id,
                "hits_view": info["hits_view"],
                "hits_tocart": info["hits_tocart"],
            })
            
        model_analysis_data.create(model_analysis_data_values)

        response_data = {"response": "success", "message": "Processed successfully"}
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )