import json

from odoo import http
from odoo.http import Response
from datetime import datetime


class AnalysysDataLotsController(http.Controller):
    @http.route("/api/v1/patch/competitors_products", 
                auth="user", 
                type="http", 
                csrf=False, 
                methods=["GET"])
    def patch_competitors_products(self, **post):
        model_products = http.request.env["ozon.products"]
        model_competitors_products = http.request.env["ozon.products_competitors"]
        
        competitors_records = model_competitors_products.search([])
        
        count_patch = 0
        for competitors_record in competitors_records:
            if competitors_record.product.id:
                product = model_products.search([("id", "=", competitors_record.product.id)])
                product.write({'competitors_with_price_ids': [(4, competitors_record.id)]})
                count_patch += 1

        response_data = {"response": "success", "message": f"Competitors records: {len(competitors_records)}, Patches records: {count_patch}"}
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )