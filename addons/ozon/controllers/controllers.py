import os

from odoo import http
from io import BytesIO


class OzonFileSend(http.Controller):
    @http.route("/download/index_local", type="http", auth="public")
    def send_file_to_user(self):
        csv_file_path = "index_local.csv"

        file_path = os.path.join(os.path.dirname(__file__), csv_file_path)

        with open(file_path, "r", encoding="utf-8") as file:
            csv_data = file.read()

        file_name = os.path.basename(file_path)

        buffer = BytesIO()

        buffer.write(csv_data.encode("utf-8"))

        response = http.Response(
            buffer.getvalue(),
            content_type="text/csv",
        )
        response.headers.add("Content-Disposition", f"attachment; filename={file_name}")
        return response
