from odoo import http


class ImportCostPrice(http.Controller):
    @http.route(
        '/api/v1/retail/import/cost_price', 
        auth='user', type='http',  csrf=False, methods=["POST"]
    )
    def import_cost_price(self, **kwargs):
        model_retail_import_file = http.request.env["retail.import_file"]
        file_storage = kwargs.get("file")
        f = file_storage.read().decode("utf-8")
        data_for_download = kwargs.get("data_for_download")
        values = {
            "data_for_download": data_for_download,
            # "file": f,
        }
        model_retail_import_file.create(values)
        return http.Response("Import successful", content_type='text/plain;charset=utf-8', status=200)
