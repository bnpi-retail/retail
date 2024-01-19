from odoo import http


class OzonUrlsImagesLotsImport(http.Controller):
    @http.route(
        "/import/ozon_urls_images_lots",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_ozon_urls_images_lots(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        file_storage = kwargs.get("file")
        f = file_storage.read().decode("utf-8")
        values = {
            "data_for_download": "ozon_urls_images_lots",
            "file": f,
        }
        model_ozon_import_file.create(values)

        return "File uploaded and processed successfully."