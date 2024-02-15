import json
import ast
import logging

from odoo import http
from odoo.http import Response, request
from datetime import datetime


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

        model_analysis_data_values = []
        for sku_date, info in data.items():
            sku, date = sku_date
            product = model_products.search(
                ['|', '|', ("sku", "=", sku), ('fbo_sku', '=', sku), ('fbs_sku', '=', sku)]
                , limit=1
            )

            model_analysis_data_values.append({
                "date": date,
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