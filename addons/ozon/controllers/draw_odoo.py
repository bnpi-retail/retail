import json
import ast

from itertools import groupby
from operator import attrgetter
from datetime import datetime, timedelta

from odoo import http
from odoo.http import Response


class DrawOdooController(http.Controller):
    
    @http.route("/api/v1/get-data-for-draw-graphs", 
                auth="user", 
                csrf=False,
                methods=["GET"])
    def get_data_for_draw(self, **kwargs):
        model_sale = http.request.env["ozon.sale"]

        current_date = datetime.now()
        current_year = datetime.combine(current_date, datetime.min.time())
        last_year = current_year - timedelta(days=365)
        year_before_last = current_year - timedelta(days=365 * 2)

        records_current_year = model_sale.search([
            ("is_calculate", "=", True),
            ("date", ">=", current_year),
        ])
        records_last_year = model_sale.search([
            ("is_calculate", "=", True),
            ("date", ">=", last_year),
            ("date", "<", current_year),
        ])
        records_year_before_last = model_sale.search([
            ("is_calculate", "=", True),
            ("date", ">=", year_before_last),
            ("date", "<", last_year),
        ])

        data_for_graph = {}
        for records in [records_current_year, records_last_year, records_year_before_last]:
            data = {}
            for record in records:
                if record.product not in data:
                    data[record.product] = []
                data[record.product].append(record)

            for product, records_list in data.items():
                if product not in data_for_graph:
                    data_for_graph[f"{product.id}--{records_list[0].date.year}"] = {"dates": [], "qty": [], "revenue": []}

                records_list.sort(key=attrgetter('date'))

                all_weeks = {i: {"qty": 0, "revenue": 0} for i in range(1, 53)}

                for record in records_list:
                    date = record.date
                    week_key = date.isocalendar()[1]

                    while week_key not in all_weeks:
                        date -= timedelta(days=1)
                        week_key = date.isocalendar()[1]

                    all_weeks[week_key]["qty"] += record.qty
                    all_weeks[week_key]["revenue"] += record.revenue

                serialized_records = [{"week": week, "qty": data["qty"], "revenue": data["revenue"]} for week, data in all_weeks.items()]

                data_for_graph[f"{product.id}--{records_list[0].date.year}"] = serialized_records

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