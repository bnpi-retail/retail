import json
import ast

from odoo import http
from odoo.http import Response, request
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
        grouped_records = records.group_by('product')

        response_data = {"response": "success", "message": f"Records for delete: {len(grouped_records)}"}
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )