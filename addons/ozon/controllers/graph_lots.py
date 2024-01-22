from odoo import http
import base64

class ImportImagesProducts(http.Controller):
    @http.route(
        "/import/images/products",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_images_products(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        uploaded_file = http.request.httprequest.files.get('file')
        file_binary_data = uploaded_file.read()
        values = {
            "data_for_download": "ozon_images_products",
            "file": base64.b64encode(file_binary_data),
        }
        model_ozon_import_file.create(values)

        return "File uploaded and processed successfully."
    
class ImportImagesCompetitorsProducts(http.Controller):
    @http.route(
        "/import/images/competitors_products",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_images_competitors_products(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        uploaded_file = http.request.httprequest.files.get('file')
        file_binary_data = uploaded_file.read()
        values = {
            "data_for_download": "ozon_images_competitors_products",
            "file": base64.b64encode(file_binary_data),
        }
        model_ozon_import_file.create(values)

        return "File uploaded and processed successfully."