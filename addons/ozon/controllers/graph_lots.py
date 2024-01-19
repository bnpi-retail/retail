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
        # model_ozon_import_file.create({
        #     "data_for_download": "ozon_urls_images_lots",
        #     "file": kwargs.get("file").read().decode("utf-8"),
        # })

        return "File uploaded and processed successfully."