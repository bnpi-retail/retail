from odoo import http


class OzonFileImport(http.Controller):
    @http.route("/import/products_from_ozon_api_to_file", auth="user", csrf=False, methods=['POST'])
    def import_products_from_ozon_api_to_file(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]

        values = {
            'data_for_download': 'ozon_products_api',
            'file': kwargs.get('file'),
        }
        
        model_ozon_import_file.create(values)

        return 'File uploaded and processed successfully.'

