import json
import base64
from odoo import http
from odoo.http import request
from odoo.http import Response


class OzonPlugin(http.Controller):
    @http.route('/take_ozon_data', auth='public', type='http', csrf=False, methods=["POST"])
    def ozon_plugin(self, **kwargs):
        uploaded_file = http.request.httprequest.files.get('file')

        if uploaded_file:
            # current_path = os.path.dirname(os.path.realpath(__file__))
            # file_path = os.path.join(current_path, uploaded_file.filename)
            # with open(file_path, 'wb') as file:
            #     file.write(uploaded_file.read())

            file_binary_data = uploaded_file.read()
            model_ozon_import_file = http.request.env["ozon.import_file"]
            model_ozon_import_file.create({
                "data_for_download": "ozon_plugin",
                "file": base64.b64encode(file_binary_data),
            })




            response_data = {'response': 'success', 'message': 'File received and processed successfully'}
            status_code = 200
        else:
            response_data = {'response': 'error', 'message': 'No file received'}
            status_code = 400

        response_json = json.dumps(response_data)
        
        response = Response(
            response=response_json,
            status=status_code,
            content_type='application/json'
        )
        
        return response