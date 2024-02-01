from odoo import http
from odoo.http import request


class DownloadDataGraph(http.Controller):
    @http.route('/web/content_text', type='http', auth="public")
    def content_text(self, model, id, field, **kwargs):
        try:
            record = request.env[model].browse(int(id))
            if record and field in record:
                return request.make_response(
                    record[field],
                    [('Content-Type', 'text/plain'), ('Content-Disposition', f'attachment; filename={model}_{id}_{field}.txt')]
                )
            else:
                return request.make_response(
                    '',
                    [('Content-Type', 'text/plain'), ('Content-Disposition', f'attachment; filename={model}_{id}_{field}.txt')]
                )
        except Exception as e:
            return str(e)
