import json

from os import getenv
from odoo import http


class GetDataForOzonProducts(http.Controller):
    @http.route("/api/v1/get_data_for_ozon_products", 
                auth="user", 
                csrf=False,
                methods=["POST"])
    def get_data_for_ozon_products(self, **kwargs):
        # unique_id = getenv("ID_KEY_OZON_PRODUCT_TASK")
        unique_id = "038d3d39-b778-499d-bceb-12fbcb40b092"

        model_ozon_temporal_tasks = http.request.env["ozon.temporal_tasks"]
        record = model_ozon_temporal_tasks.search([("unique_id", "=", unique_id)])
        data = json.dumps({
            "limit": record.numbers_products_in_query,
            "workers": record.numbers_workers
        })
        return http.Response(data, content_type="application/json")
