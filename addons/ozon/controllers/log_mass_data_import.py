import datetime
import logging
import traceback

from odoo import http

logger = logging.getLogger(__name__)


class MassDataImportController(http.Controller):
    @http.route("/api/v1/mass-data-import",
                auth="user",
                type="json",
                methods=["POST", "PUT"])
    def mass_data_import(self):
        if http.request.httprequest.method == 'POST':
            try:
                request_data = http.Request.get_json_data(http.request).get('data')
                mdi_model = http.request.env["ozon.mass_data_import.log"]
                log = mdi_model.create({
                    'name': request_data.get('name')
                })
                log_id = log.id

                response_data = {"response": "success", "message": "Processed successfully", 'log_id': log_id}
            except Exception as e:
                logger.warning(f"create_mass_data_import exception: {e}, {traceback.format_exc()} ")
                response_data = {"response": "server error", "message": "Process error"}

            return response_data

        elif http.request.httprequest.method == 'PUT':
            try:
                request_data = http.Request.get_json_data(http.request).get('data')
                mdi_model = http.request.env["ozon.mass_data_import.log"]
                log = mdi_model.browse([request_data.get('log_id')])
                state = request_data.get('state')
                log_value = request_data.get('log_value')
                displaying_data_raw = request_data.get('activity_data')
                dd_list = [f"{key}: {value}\n" for key, value in displaying_data_raw.items()]
                displaying_data = ''.join(dd_list)

                vals = {
                    'state': state,
                    'displaying_data': displaying_data,
                    'log_value': log_value,
                    'finish_time': datetime.datetime.now(),
                }
                log.write(vals)
            except Exception:
                logger.error(traceback.format_exc())

