import json
import ast
import logging
from odoo import http

logger = logging.getLogger(__name__)


class MassDataImportController(http.Controller):
    @http.route("api/v1/create-mass-data-import",
                auth="user",
                type="http",
                csrf=False,
                methods=["POST"])
    def save_analysys_data_lots(self, data, **post):
        try:
            logging.warning(self)
            logging.warning(data)
            logging.warning(post)

            model_products = http.request.env["ozon.products"]


            response_data = {"response": "success", "message": "Processed successfully"}
            response_json = json.dumps(response_data)
            status_code = 200
        except:
            pass

        return http.Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )