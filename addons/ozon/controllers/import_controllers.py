import logging
import time
import json
import traceback

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
        log_data = model_ozon_import_file.import_file(values)
        response_json = json.dumps(log_data)

        return response_json


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
        try:
            log_data = model_ozon_import_file.import_file(values)
            response_json = json.dumps(log_data)
        except Exception as e:
            raise Exception(f"ozon_import_file error: {e} {traceback.format_exc()}")
        return response_json


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
        log_data = model_ozon_import_file.import_file(values)
        response_json = json.dumps(log_data)

        return response_json


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
        log_data: dict = model_ozon_import_file.import_file(values)
        response_json = json.dumps(log_data)

        return response_json


class OzonPostingsImport(http.Controller):
    @http.route(
        "/import/postings_from_ozon_api_to_file",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_postings_from_ozon_api_to_file(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        file_storage = kwargs.get("file")
        f = file_storage.read().decode("utf-8")
        values = {
            "data_for_download": "ozon_postings",
            "file": f,
        }
        log_data = model_ozon_import_file.import_file(values)
        response_json = json.dumps(log_data)

        return response_json


class OzonFboSupplyOrdersImport(http.Controller):
    @http.route(
        "/import/fbo_supply_orders_from_ozon_api_to_file",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_fbo_supply_orders_from_ozon_api_to_file(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        file_storage = kwargs.get("file")
        f = file_storage.read().decode("utf-8")
        values = {
            "data_for_download": "ozon_fbo_supply_orders",
            "file": f,
        }
        log_data = model_ozon_import_file.import_file(values)
        response_json = json.dumps(log_data)

        return response_json


class OzonActionsImport(http.Controller):
    @http.route(
        "/import/ozon_actions",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def import_ozon_actions(self, **kwargs):
        model_ozon_import_file = http.request.env["ozon.import_file"]
        file_storage = kwargs.get("file")
        f = file_storage.read().decode("utf-8")
        values = {
            "data_for_download": "ozon_actions",
            "file": f,
        }
        log_data = model_ozon_import_file.import_file(values)
        response_json = json.dumps(log_data)

        return response_json
