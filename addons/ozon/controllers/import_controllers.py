from odoo import http


class OzonTransactionsImport(http.Controller):
    @http.route(
        "/import/transactions_from_ozon_api_to_file",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_transactions_from_ozon_api_to_file(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        file_storage = kwargs.get("file")
        f = file_storage.read().decode("utf-8")
        values = {
            "data_for_download": "ozon_transactions",
            "file": f,
        }
        model_ozon_import_file.create(values)

        return "File uploaded and processed successfully."


class OzonProductsImport(http.Controller):
    @http.route(
        "/import/products_from_ozon_api_to_file",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_products_from_ozon_api_to_file(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        file_storage = kwargs.get("file")
        f = file_storage.read().decode("utf-8")
        values = {
            "data_for_download": "ozon_products",
            "file": f,
        }
        model_ozon_import_file.create(values)

        return "File uploaded and processed successfully."


class OzonStocksImport(http.Controller):
    @http.route(
        "/import/stocks_from_ozon_api_to_file",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_stocks_from_ozon_api_to_file(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        file_storage = kwargs.get("file")
        f = file_storage.read().decode("utf-8")
        values = {
            "data_for_download": "ozon_stocks",
            "file": f,
        }
        model_ozon_import_file.create(values)

        return "File uploaded and processed successfully."


class OzonPricesImport(http.Controller):
    @http.route(
        "/import/prices_from_ozon_api_to_file",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_prices_from_ozon_api_to_file(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        file_storage = kwargs.get("file")
        f = file_storage.read().decode("utf-8")
        values = {
            "data_for_download": "ozon_prices",
            "file": f,
        }
        model_ozon_import_file.create(values)

        return "File uploaded and processed successfully."
