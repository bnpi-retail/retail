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
                mdi_model = http.request.env["ozon.mass_data_import"]
                import_ = mdi_model.create({
                    'name': request_data.get('name'),
                    'expected_quantity': request_data.get('logged_activities_qty'),
                })
                import_id = import_.id

                response_data = {"response": "success", "message": "Processed successfully", 'import_id': import_id}
            except Exception as e:
                logger.warning(f"create_mass_data_import exception: {e}, {traceback.format_exc()} ")
                response_data = {"response": "server error", "message": "Process error"}

            return response_data

    @http.route("/api/v1/mass-data-import-log",
                auth="user",
                type="json",
                methods=["POST", "PUT"])
    def mass_data_import_log(self):
        if http.request.httprequest.method == 'POST':
            try:
                request_data = http.Request.get_json_data(http.request).get('data')
                mass_import_id = http.request.env["ozon.mass_data_import"].search([
                    ('create_date', '>', datetime.date.today() - datetime.timedelta(days=1)),
                    ('state', '=', 'running')
                ], order='create_date desc', limit=1).id

                mdi_model = http.request.env["ozon.mass_data_import.log"]
                log = mdi_model.create({
                    'name': request_data.get('name'),
                    'ozon_mass_data_import_id': mass_import_id,
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
                dd_list = ['']
                if displaying_data_raw:
                    dd_list = [f"{key}: {value}\n" for key, value in displaying_data_raw.items()]
                displaying_data = ''.join(dd_list)
                mass_import_id = log.ozon_mass_data_import_id.id
                mass_import = http.request.env["ozon.mass_data_import"].browse([mass_import_id])

                vals = {
                    'state': state,
                    'displaying_data': displaying_data,
                    'log_value': log_value,
                    'finish_time': datetime.datetime.now(),
                }
                log.write(vals)
                mass_import.executed_quantity += 1
            except Exception:
                logger.error(traceback.format_exc())

