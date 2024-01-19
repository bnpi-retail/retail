import json
from itertools import groupby
from odoo import http
from odoo.http import Response
from datetime import datetime


class AnalysysDataLotsController(http.Controller):
    @http.route("/api/v1/delete_dublicate_stock_records", 
                auth="user", 
                type="http", 
                csrf=False, 
                methods=["GET"])
    def delete_dublicate_stock_records(self, **post):
        model_products = http.request.env["ozon.stock"]
        
        target_date = datetime.strptime('01.16.24', '%m.%d.%y')
        records = model_products.search([('timestamp', '=', target_date.strftime('%Y-%m-%d %H:%M:%S'))])
        sorted_records = records.sorted(key=lambda r: (r.product.id, r.timestamp), reverse=True)
        grouped_records = {key: list(group) for key, group in groupby(sorted_records, key=lambda r: r.product.id)}

        records_to_keep = model_products
        for product_id, group in grouped_records.items():
            latest_record = max(group, key=lambda r: r.timestamp)
            records_to_keep |= latest_record

        response_data = {"response": "success", "message": f"Records for delete: {len(records_to_keep)}"}
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )