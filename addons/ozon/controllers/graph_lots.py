from odoo import http
import base64

class ImportImagesSale(http.Controller):
    @http.route(
        "/import/images",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_images_sale(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        uploaded_file = http.request.httprequest.files.get('file')
        file_binary_data = uploaded_file.read()
        model = http.request.params.get('model')

        values = {
            "model": model,
            "data_for_download": "ozon_images",
            "file": base64.b64encode(file_binary_data),
        }
        model_ozon_import_file.create(values)

        return "File uploaded and processed successfully."