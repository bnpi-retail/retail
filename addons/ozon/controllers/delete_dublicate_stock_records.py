import json

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
        model_stock = http.request.env["ozon.stock"]
        
        target_date = datetime.strptime('01.16.24', '%m.%d.%y')
        records = model_stock.search([('timestamp', '=', target_date.strftime('%Y-%m-%d %H:%M:%S'))])

        records_unique = set()
        records_to_remove = []

        for record in records[:1000]:
            if record.product.id in records_unique:
                records_to_remove.append(record.id)
            else:
                records_unique.add(record.product.id)

        for id in records_to_remove:
            model_stock.search([("id", "=", id)]).unlink()

        response_data = {"response": "success", "message": f"Records for delete: {len(records_to_remove)}"}
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )