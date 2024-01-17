import json
import ast

from itertools import groupby
from operator import attrgetter

from odoo import http
from odoo.http import Response


class DrawOdooController(http.Controller):
    
    @http.route("/api/v1/get-data-for-draw-graphs", 
                auth="user", 
                csrf=False,
                methods=["GET"])
    def get_data_for_draw(self, **kwargs):
        model_sale = http.request.env["ozon.sale"]
        records = model_sale.search([("is_calculate", "=", True)])

        data = {}
        for record in records:
            if record.product not in data:
                data[record.product] = []
            data[record.product].append(record)
        
        data_for_graph = {}
        for product, records_list in data.items():
            if product not in data_for_graph:
                data_for_graph[product.id] = {"dates": [], "qty": [], "revenue": []}

            records_list.sort(key=attrgetter('date'))
            grouped_records = {date.strftime("%Y-%m-%d"): list(group) for date, group in groupby(records_list, key=lambda x: x.date)}

            data_for_graph[product.id] = grouped_records
            # for record in records_list:
            #     data_for_graph[product.id]["dates"].append(record.date.strftime("%Y-%m-%d"))
            #     data_for_graph[product.id]["qty"].append(record.qty)

        json_response = json.dumps(data_for_graph)
        return http.Response(json_response, content_type="application/json")

    @http.route("/api/v1/api/v1/save-images-for-lots", 
                auth="user", 
                type="http", 
                csrf=False, 
                methods=["POST"])
    def save_images(self, data, **post):
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