import base64

from odoo import http


class ImportCostPrice(http.Controller):
    @http.route(
        "/api/v1/retail/import/cost_price",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_images_sale(self, **kwargs):
        model_retail_import_file = http.request.env["retail.import_file"]
        uploaded_file = http.request.httprequest.files.get('file')
        file_binary_data = uploaded_file.read()
        data_for_download =  http.request.params.get("data_for_download")

        values = {
            "data_for_download": data_for_download,
            "file": base64.b64encode(file_binary_data),
        }

        # model_retail_import_file.create(values)
        
        return "File uploaded and processed successfully."