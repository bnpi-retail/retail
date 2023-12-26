import json
import base64
from odoo import http
from odoo.http import request
from odoo.http import Response


class OzonPlugin(http.Controller):
    @http.route('/take_ozon_data', auth='user', type='http', csrf=False, methods=["POST"])
    def ozon_plugin(self, **kwargs):
        uploaded_file = http.request.httprequest.files.get('file')
        email = http.request.params.get('email')
        worker = request.env['res.users'].search([('email', '=', email)])

        if uploaded_file:
            file_binary_data = uploaded_file.read()
            model_ozon_import_file = http.request.env["ozon.import_file"]
            model_ozon_import_file.create({
                "worker": worker.id,
                "data_for_download": "ozon_plugin",
                "file": base64.b64encode(file_binary_data),
            })
            response_data = {'response': 'success', 'message': 'File received and processed successfully'}
            status_code = 200
        else:
            response_data = {'response': 'error', 'message': 'No file received'}
            status_code = 400

        response_json = json.dumps(response_data)
        
        return Response(
            response=response_json,
            status=status_code,
            content_type='application/json'
        )
    
    @http.route('/take_requests', auth='user', type='http', csrf=False, methods=["POST"])
    def ozon_requests(self, **kwargs):

        record = request.env['ozon.search_query_queue'] \
            .search([('status', '=', 'available')], limit=1)
        
        length_query = 0
        if record:
            record.write({'status': 'in_processing'})
            length_query = 1

        response_data = {
            'response': 'success',
            'length_query': length_query,
            'searches': [record.query],
        }
        response_json = json.dumps(response_data)
        
        return Response(
            response=response_json,
            status=200,
            content_type='application/json'
        )