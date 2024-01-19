from odoo import http
import base64

class OzonUrlsImagesLotsImport(http.Controller):
    @http.route(
        "/import/ozon_urls_images_lots",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_ozon_urls_images_lots(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        uploaded_file = http.request.httprequest.files.get('file')
        file_binary_data = uploaded_file.read()
        values = {
            "data_for_download": "ozon_urls_images_lots",
            "file": base64.b64encode(file_binary_data),
        }
        model_ozon_import_file.create(values)

        return "File uploaded and processed successfully."