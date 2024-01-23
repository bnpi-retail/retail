import json

from odoo import http
from odoo.http import Response
from datetime import datetime


class PatchAnalysysDataLotsController(http.Controller):
    @http.route("/api/v1/delete_dublicate_stock_records", 
                auth="user", 
                type="http", 
                csrf=False, 
                methods=["GET"])
    def delete_dublicate_stock_records(self, **post):
        model_stock = http.request.env["ozon.stock"]
        
        target_date = datetime.strptime('01.16.24', '%m.%d.%y')
        records = model_stock.search([('timestamp', '=', target_date.strftime('%Y-%m-%d %H:%M:%S'))])

        records_unique = set()
        records_to_remove = []

        for record in records:
            if record.product.id in records_unique:
                records_to_remove.append(record.id)
            else:
                records_unique.add(record.product.id)

        for id in records_to_remove[:4000]:
            model_stock.search([("id", "=", id)]).unlink()
                
        response_data = {"response": "success", "message": f"Records for delete: {len(records_to_remove)}, All records: {len(records_unique)}"}
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )


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
            for price_history_id in product.competitors_with_price_ids.ids:
                price_history_record = model_price_history_competitors.search([("id", "=", price_history_id)])
                
                if price_history_competitor_record.product_competitors.id == price_history_record.product_competitors.id:
                    product.write({'competitors_with_price_ids': [(3, price_history_record.id)]})
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
    

class PatchArticle(http.Controller):
    @http.route("/api/v1/patch/article/products_and_competitors_products", 
                auth="user", 
                type="http", 
                csrf=False, 
                methods=["GET"])
    def patch_article(self, **post):
        model_products = http.request.env["ozon.products"]
        
        count_products = 0
        products = model_products.search([], limit=1000)
        for product in products:
            if product.article: continue

            product.article = product.products.product_id
            count_products += 1

        model_products_competitors = http.request.env["ozon.products_competitors"]

        count_competitors_products = 0
        products_competitors = model_products_competitors.search([])
        for competitors_product in products_competitors:
            if competitors_product.article: continue

            competitors_product.article = competitors_product.product.products.product_id
            count_competitors_products += 1

        response_data = {
            "response": "success", "message": 
            f"Articles update in products: {count_products}, " 
            f"Articles update in competitors products: {count_competitors_products}"
        }
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )