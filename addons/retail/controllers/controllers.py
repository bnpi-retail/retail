
from odoo import http


class Retail(http.Controller):
    @http.route('/retail/improt_file_1C', auth='public', csrf=False)
    def improt_file_1C(self, **kw):
        
        model_retail_import_file = http.request.env['retail.import_file']
        values = {'data_for_download': 'cost_price'}
        model_retail_import_file.create(values)
        
        return "Import successful"
