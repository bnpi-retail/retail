import json
from itertools import groupby
from odoo import http
from odoo.http import Response
from datetime import datetime
from collections import defaultdict

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

        latest_records = defaultdict(lambda: None)

        records_to_keep = model_products
        for record in records.sorted(key=lambda r: (r.product.id, r.timestamp), reverse=True):
            if latest_records[record.product.id] is None:
                latest_records[record.product.id] = record
                records_to_keep |= record

        response_data = {"response": "success", "message": f"Records for delete: {len(records_to_keep)}"}
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )