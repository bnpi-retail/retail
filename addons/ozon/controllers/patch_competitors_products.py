import json

from odoo import http
from odoo.http import Response


class PatchCompetitorsProductsController(http.Controller):
    @http.route("/api/v1/patch/competitors_products", 
                auth="user", 
                type="http", 
                csrf=False, 
                methods=["GET"])
    def patch_competitors_products(self, **post):
        model_products = http.request.env["ozon.products"]
        model_price_history_competitors = http.request.env["ozon.price_history_competitors"]
        
        price_history_competitors_records = model_price_history_competitors.search([])
        
        count_patch = 0
        for price_history_competitor_record in price_history_competitors_records:
            product_id = price_history_competitor_record.product_competitors.product.id

            if not product_id: continue
        
            product = model_products.search([("id", "=", product_id)])

            new = True
            for price_history_id in product.competitors_with_price_ids:
                price_history_record = model_price_history_competitors.browse(price_history_id.id)
                
                if price_history_competitor_record.product_competitors.id == price_history_record.product_competitors.id:
                    product.write({'competitors_with_price_ids': [(3, price_history_record)]})
                    product.write({'competitors_with_price_ids': [(4, price_history_competitor_record.id)]})
                    count_patch += 1
                    new = False

            if new == True:
                product.write({'competitors_with_price_ids': [(4, price_history_competitor_record.id)]})
                count_patch += 1

        response_data = {"response": "success", "message": f"Competitors records: {len(price_history_competitors_records)}, Patches records: {count_patch}"}
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )