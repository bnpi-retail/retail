import ast
import base64
import csv
import logging
import openpyxl
import magic
import json
import os
import timeit

from io import BytesIO, StringIO
from typing import Any
from datetime import date, datetime
from collections import defaultdict
from multiprocessing import Value
from odoo import models, fields, api, exceptions
from odoo.exceptions import UserError
from .competitors.competitor_sale import ProductCompetitorSale

logger = logging.getLogger()

from ..ozon_api import (
    ALL_COMMISSIONS,
    get_product_id_by_sku,
)

from ..helpers import convert_ozon_datetime_str_to_odoo_datetime_str


class ImportFile(models.Model):
    _name = "ozon.import_file"
    _description = "Импорт"
    _order = "timestamp desc"

    timestamp = fields.Date(
        string="Дата импорта", default=fields.Date.today, readonly=True
    )
    model = fields.Char(string="К какой модели относиться график")

    data_for_download = fields.Selection(
        [
            ("ozon_products", "Товары Ozon"),
            ("ozon_plugin", "Товары Ozon (Плагин)"),
            ("ozon_commissions", "Комиссии Ozon по категориям"),
            ("ozon_transactions", "Транзакции Ozon"),
            ("ozon_stocks", "Остатки товаров Ozon"),
            ("ozon_prices", "Цены Ozon"),
            ("ozon_images", "Ссылки на графики"),
            ("ozon_successful_products_competitors", "Успешные товары конкурентов"),
            ("ozon_postings", "Отправления Ozon"),
            ("ozon_fbo_supply_orders", "Поставки FBO"),
            ("ozon_actions", "Акции Ozon"),
            ("ozon_competitors_goods", "Товары ближайших конкурентов Ozon с продажами"),
            (
                "ozon_ad_campgaign_search_promotion_report",
                "Отчёт о рекламной кампании (продвижение в поиске)",
            ),
            ("ozon_realisation_report", "Отчёт о реализации товаров"),
        ],
        string="Данные для загрузки",
    )

    file = fields.Binary(
        attachment=True, string="Файл для загрузки своих данных", help="Выбрать файл"
    )

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            id = record.id
            name = f"Загруженный файл № {id}"
            result.append((id, name))
        return result

    def get_file_mime_type(self, file_content):
        mime = magic.Magic()
        file_type = mime.from_buffer(file_content)
        return file_type

    @api.model
    def create(self, values):
        if not "file" in values or not values["file"]:
            raise exceptions.ValidationError("Отсутствует файл.")

        if not "data_for_download" in values or not values["data_for_download"]:
            raise exceptions.ValidationError("Необходимо выбрать 'данные для загрузки'")

        if values["data_for_download"] == "ozon_competitors_goods":
            workbook = openpyxl.load_workbook(BytesIO(base64.b64decode(values["file"])))
            self._parse_ozon_competitors_goods_xlsx_file(workbook)
            return super(ImportFile, self).create(values)

        content = base64.b64decode(values["file"])
        mime_type = self.get_file_mime_type(content)
        mime_type = mime_type.lower()

        content = content.decode("utf-8")
        lines = content.split("\n")

        if values["data_for_download"] == "ozon_images":
            if values["model"] == "sale":
                self.import_images_sale(content)

            elif values["model"] == "sale_by_week":
                self.import_images_sale_by_week(content)

            elif values["model"] == "competitors_products":
                self.import_images_competitors_products(content)

            elif values["model"] == "price_history":
                self.import_images_price_history(content)

            elif values["model"] == "stock":
                self.import_images_stock(content)

            elif values["model"] == "analysis_data":
                self.import_images_analysis_data(content)

            elif values["model"] == "categorie_analysis_data":
                self.import_images_categorie_analysis_data(content)

            elif values["model"] == "categorie_sale_this_year":
                self.import_images_categorie_categorie_sale_this_year(content)

            elif values["model"] == "categorie_sale_last_year":
                self.import_images_categorie_categorie_sale_last_year(content)

        if values["data_for_download"] == "ozon_successful_products_competitors":
            self.import_successful_products_competitors(content)

        if values["data_for_download"] == "ozon_ad_campgaign_search_promotion_report":
            self.import_ad_campgaign_search_promotion_report(content)

        if values["data_for_download"] == "ozon_realisation_report":
            self.import_ozon_realisation_report(content)

        if "csv" in mime_type:
            if values["data_for_download"] == "ozon_products":
                f_path = "/mnt/extra-addons/ozon/products_from_ozon_api.csv"
                with open(f_path, "w") as f:
                    f.write(content)

                with open(f_path) as csvfile:
                    price_history_data_list = []
                    reader = csv.DictReader(csvfile)
                    for i, row in enumerate(reader):
                        row_id_on_platform = row["id_on_platform"]
                        row_price = row["price"]
                        row_old_price = row["old_price"]
                        row_name = row["name"]
                        row_description = row["description"]
                        row_keywords = row["keywords"]
                        row_categories = row["categories"]
                        row_c_id = row["description_category_id"]

                        # s0 = timeit.default_timer()
                        if ozon_product := self.is_ozon_product_exists(
                            id_on_platform=row_id_on_platform
                        ):
                            ozon_product.write(
                                {
                                    "sku": row["sku"],
                                    "fbo_sku": row["fbo_sku"],
                                    "fbs_sku": row["fbs_sku"],
                                    "trading_scheme": row["trading_scheme"],
                                    "price": row["price"],
                                    "old_price": row["old_price"],
                                    "ext_comp_min_price": row["ext_comp_min_price"],
                                    "ozon_comp_min_price": row["ozon_comp_min_price"],
                                    "self_marketplaces_min_price": row[
                                        "self_marketplaces_min_price"
                                    ],
                                    "price_index": row["price_index"],
                                    "imgs_urls": row["img_urls"],
                                }
                            )
                            ozon_product.products.write(
                                {
                                    "name": row_name,
                                    "description": row_description,
                                    "keywords": row_keywords,
                                }
                            )
                            ozon_product.categories.write(
                                {"name_categories": row_categories, "c_id": row_c_id}
                            )

                        else:
                            if ozon_category := self.is_ozon_category_exists_by_id(
                                row_c_id
                            ):
                                pass
                            else:
                                ozon_category = self.env["ozon.categories"].create(
                                    {
                                        "name_categories": row_categories,
                                        "c_id": row_c_id,
                                    }
                                )
                            if seller := self.is_retail_seller_exists(
                                row["seller_name"]
                            ):
                                pass
                            else:
                                seller = self.env["retail.seller"].create(
                                    {
                                        "name": "Продавец",
                                        "tax": "earnings_6",
                                    }
                                )

                            retail_product = self.env["retail.products"].create(
                                {
                                    "name": row_name,
                                    "description": row_description,
                                    "keywords": row_keywords,
                                    "product_id": row["offer_id"],
                                    "length": float(row["length"]),
                                    "width": float(row["width"]),
                                    "height": float(row["height"]),
                                    "weight": float(row["weight"]),
                                }
                            )

                            ozon_product = self.env["ozon.products"].create(
                                {
                                    "id_on_platform": row_id_on_platform,
                                    "sku": row["sku"],
                                    "fbo_sku": row["fbo_sku"],
                                    "fbs_sku": row["fbs_sku"],
                                    "categories": ozon_category.id,
                                    "article": retail_product.product_id,
                                    "description": row_description,
                                    "products": retail_product.id,
                                    "price": row_price,
                                    "old_price": row_old_price,
                                    "ext_comp_min_price": row["ext_comp_min_price"],
                                    "ozon_comp_min_price": row["ozon_comp_min_price"],
                                    "self_marketplaces_min_price": row[
                                        "self_marketplaces_min_price"
                                    ],
                                    "price_index": row["price_index"],
                                    "imgs_urls": row["img_urls"],
                                    "seller": seller.id,
                                    "trading_scheme": row["trading_scheme"],
                                }
                            )

                            print(f"product {row_id_on_platform} created")

                        ozon_product_id = ozon_product.id
                        # s1 = timeit.default_timer()
                        ozon_product.populate_search_queries(row_keywords)
                        ozon_product.populate_supplementary_categories(
                            row["full_categories"],
                            row["full_categories_id"],
                        )
                        # s2 = timeit.default_timer()
                        all_fees = {k: row[k] for k in ALL_COMMISSIONS.keys()}

                        if product_fee := ozon_product.product_fee:
                            # TODO: удалить, когда во всех комиссиях запишется product_id_on_platform
                            product_fee.write(
                                {"product_id_on_platform": row_id_on_platform}
                            )
                            are_fees_the_same = True
                            for key, new_value in all_fees.items():
                                if product_fee[key] != float(new_value):
                                    are_fees_the_same = False
                                    product_fee.write(
                                        {
                                            "product_id_on_platform": row_id_on_platform,
                                            **all_fees,
                                        }
                                    )
                                    break
                        else:
                            are_fees_the_same = False
                            product_fee = self.env["ozon.product_fee"].create(
                                {
                                    "product": ozon_product_id,
                                    "product_id_on_platform": row_id_on_platform,
                                    **all_fees,
                                }
                            )
                            ozon_product.write({"product_fee": product_fee.id})

                        # s3 = timeit.default_timer()
                        if are_fees_the_same:
                            fix_expenses_ids = ozon_product.fix_expenses.ids
                            percent_expenses_ids = ozon_product.percent_expenses.ids
                        else:
                            fix_expenses = self.env[
                                "ozon.fix_expenses"
                            ].create_from_ozon_product_fee(product_fee)
                            fix_expenses_ids = fix_expenses.ids
                            percent_expenses = self.env[
                                "ozon.cost"
                            ].create_from_ozon_product_fee(
                                product_fee=product_fee,
                                price=ozon_product.price,
                            )
                            percent_expenses_ids = percent_expenses.ids

                            ozon_product.write(
                                {
                                    "fix_expenses": fix_expenses_ids,
                                    "percent_expenses": percent_expenses_ids,
                                },
                                percent_expenses=percent_expenses,
                            )
                        # s4 = timeit.default_timer()

                        price_history_records = (
                            ozon_product.price_our_history_ids.sorted(
                                key=lambda r: r.create_date, reverse=True
                            )
                        )

                        # s41 = timeit.default_timer()
                        if price_history_records:
                            previous_price = price_history_records[0].price
                        else:
                            previous_price = 0

                        # s42 = timeit.default_timer()
                        price_history_data = {
                            "product": ozon_product_id,
                            "id_on_platform": row_id_on_platform,
                            "provider": ozon_product.seller.id,
                            "price": float(row_price),
                            "previous_price": previous_price,
                            "fix_expenses": fix_expenses_ids,
                            "costs": percent_expenses_ids,
                        }
                        price_history_data_list.append(price_history_data)
                        print(
                            f"{i} - Price history for product {row['id_on_platform']} added"
                        )
                        # s5 = timeit.default_timer()
                        # print(f"total: {s5-s0}")
                        # print(f"update ozon_product: {s1-s0}")
                        # print(f"keywords & categories: {s2-s1}")
                        # print(f"product_fee: {s3-s2}")
                        # print(f"fix_&_percent_expenses: {s4-s3}")
                        # print(f"price_history_total: {s5-s4}")
                        # print(f"is_ozon_price_history_exists: {s41-s4}")
                        # print(f"prev_price: {s42-s41}")

                    ozon_price_history = self.env["ozon.price_history"].create(
                        price_history_data_list
                    )
                os.remove(f_path)

            elif values["data_for_download"] == "ozon_commissions":
                f_path = (
                    "/mnt/extra-addons/ozon/__pycache__/commissions_from_ozon_api.csv"
                )
                with open(f_path, "w") as f:
                    f.write(content)

                with open(f_path) as csvfile:
                    reader = csv.DictReader(csvfile)
                    for i, row in enumerate(reader):
                        result = self.is_ozon_fee_exists(
                            category_name=row["category_name"],
                            commission_name=row["commission_name"],
                        )
                        if result:
                            continue

                        row_c_id = row["description_category_id"]
                        row_category_name = row["category_name"]
                        if ozon_category := self.is_ozon_category_exists_by_id(
                            row_c_id
                        ):
                            ozon_category.write(
                                {"c_id": row_c_id, "name_categories": row_category_name}
                            )
                        else:
                            ozon_category = self.env["ozon.categories"].create(
                                {"c_id": row_c_id, "name_categories": row_category_name}
                            )

                        self.env["ozon.ozon_fee"].create(
                            {
                                "name": row["commission_name"],
                                "value": row["value"],
                                "category": ozon_category.id,
                                "type": row["commission_type"],
                                "trading_scheme": row["trading_scheme"],
                            }
                        )
                        print(f"{i}th commission was created")

                os.remove(f_path)

            elif values["data_for_download"] == "ozon_transactions":
                self.import_transactions(content)
            elif values["data_for_download"] == "ozon_stocks":
                self.import_stocks(content)
            elif values["data_for_download"] == "ozon_prices":
                self.import_prices(content)
            elif values["data_for_download"] == "ozon_postings":
                self.import_postings(content)
            elif values["data_for_download"] == "ozon_fbo_supply_orders":
                self.import_fbo_supply_orders(content)
            elif values["data_for_download"] == "ozon_actions":
                self.import_actions(content)

        return super(ImportFile, self).create(values)

    def is_ozon_product_exists(self, id_on_platform: str):
        result = self.env["ozon.products"].search(
            [("id_on_platform", "=", id_on_platform)],
            limit=1,
        )
        return result if result else False

    def is_ozon_product_exists_by_sku(self, sku: str):
        result = self.env["ozon.products"].search(
            ["|", "|", ("sku", "=", sku), ("fbo_sku", "=", sku), ("fbs_sku", "=", sku)],
            limit=1,
        )
        return result if result else False

    def is_ozon_category_exists_by_name(self, category_name):
        result = self.env["ozon.categories"].search(
            [("name_categories", "=", category_name)],
            limit=1,
        )
        return result if result else False

    def is_ozon_category_exists_by_id(self, category_id):
        result = self.env["ozon.categories"].search([("c_id", "=", category_id)])
        return result if result else False

    def is_retail_product_exists(self, product_id):
        result = self.env["retail.products"].search(
            [("product_id", "=", product_id)],
            limit=1,
        )
        return result if result else False

    def is_retail_seller_exists(self, seller_name):
        result = self.env["retail.seller"].search(
            [("name", "=", seller_name)],
            limit=1,
        )
        return result if result else False

    def is_ozon_fee_exists(self, category_name, commission_name):
        result = self.env["ozon.ozon_fee"].search(
            [
                ("category.name_categories", "=", category_name),
                ("name", "=", commission_name),
            ],
            limit=1,
        )
        return result if result else False

    def is_ozon_transaction_exists(self, transaction_id):
        result = self.env["ozon.transaction"].search(
            [("transaction_id", "=", transaction_id)],
            limit=1,
        )
        return result if result else False

    def is_ozon_service_exists(self, service_name):
        result = self.env["ozon.ozon_services"].search(
            [("name", "=", service_name)],
            limit=1,
        )
        return result if result else False

    def is_stock_exists(self, ozon_product_id):
        result = self.env["ozon.stock"].search(
            [("product", "=", ozon_product_id)],
            limit=1,
            order="create_date desc",
        )
        return result if result else False

    def import_transactions(self, content):
        f_path = "/mnt/extra-addons/ozon/__pycache__/transactions.csv"
        with open(f_path, "w") as f:
            f.write(content)

        with open(f_path) as csvfile:
            reader = csv.DictReader(csvfile)
            all_transactions = (
                self.env["ozon.transaction"]
                .search([])
                .mapped(lambda r: r.transaction_id)
            )
            all_transactions = dict.fromkeys(all_transactions, True)
            transactions_data = []
            for i, row in enumerate(reader):
                if all_transactions.get(row["transaction_id"]):
                    print(f"{i} - Transaction already exists")
                    continue
                ozon_products = []
                ozon_products_ids = []
                skus = ast.literal_eval(row["product_skus"])
                for sku in skus:
                    if ozon_product := self.is_ozon_product_exists_by_sku(sku):
                        pass
                    else:
                        # обратиться в озон - есть ли такой товар по этому sku?
                        product_id = get_product_id_by_sku([sku])
                        if product_id:
                            ozon_product = self.is_ozon_product_exists(product_id[0])
                        else:
                            # TODO: что делать, если указанного в транзакции sku нет ни у нас, ни в озоне
                            continue
                    ozon_products.append(ozon_product)
                    ozon_products_ids.append(ozon_product.id)

                # TODO: как быть с транзакциями, где указанных sku нет в нашей системе? 
                # или напр. в транзакции 2 sku, один из них есть у нас, другого нет.
                # if len(skus) != len(ozon_products):
                #     print(f"{i} -")
                #     continue

                ozon_services = []
                service_list = ast.literal_eval(row["services"])
                services_cost = 0
                for name, price in service_list:
                    service = self.env["ozon.ozon_services"].create(
                        {"name": name, "price": price}
                    )
                    ozon_services.append(service.id)
                    services_cost += price
                tran_data = {
                    "transaction_id": str(row["transaction_id"]),
                    "transaction_date": row["transaction_date"],
                    "order_date": row["order_date"],
                    "name": row["name"],
                    "accruals_for_sale": row["accruals_for_sale"],
                    "sale_commission": row["sale_commission"],
                    "transaction_type": row["type"],
                    "amount": row["amount"],
                    "skus": skus,
                    "products": ozon_products_ids,
                    "services": ozon_services,
                    "posting_number": row["posting_number"],
                }
                transactions_data.append(tran_data)

                print(f"{i} - Transaction {row['transaction_id']} was created")
                # creating ozon.sale records
                if row["name"] == "Доставка покупателю":
                    self.create_sale_from_transaction(data=tran_data, 
                        products=ozon_products, services_cost=services_cost)
            self.env["ozon.transaction"].create(transactions_data)
        os.remove(f_path)

    def import_stocks(self, content):
        f_path = "/mnt/extra-addons/ozon/__pycache__/stocks.csv"
        with open(f_path, "w") as f:
            f.write(content)

        with open(f_path) as csvfile:
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader):
                id_on_platform = row["id_on_platform"]
                if ozon_product := self.is_ozon_product_exists(id_on_platform):
                    stock = self.env["ozon.stock"].create(
                        {
                            "product": ozon_product.id,
                            "id_on_platform": id_on_platform,
                            "stocks_fbs": row["stocks_fbs"],
                            "stocks_fbo": row["stocks_fbo"],
                        }
                    )
                    stocks_by_warehouse = ast.literal_eval(row["stocks_fbs_warehouses"])
                    data = []
                    for item in stocks_by_warehouse:
                        warehouse = self.get_or_create_warehouse(
                            warehouse_id=item["warehouse_id"],
                            warehouse_name=item["warehouse_name"],
                        )
                        qty = item["present"]
                        data.append(
                            {
                                "stock_id": stock.id,
                                "product_id": ozon_product.id,
                                "warehouse_id": warehouse.id,
                                "qty": qty,
                            }
                        )
                    fbs_warehouse_product_stock_ids = (
                        self.env["ozon.fbs_warehouse_product_stock"].create(data).ids
                    )
                    stock.write(
                        {
                            "fbs_warehouse_product_stock_ids": fbs_warehouse_product_stock_ids
                        }
                    )
                    ozon_product.write(
                        {
                            "stocks_fbs": row["stocks_fbs"],
                            "stocks_fbo": row["stocks_fbo"],
                        }
                    )
                    print(f"{i} - Product {id_on_platform} stock history was created")
        os.remove(f_path)

    def import_prices(self, content):
        f_path = "/mnt/extra-addons/ozon/__pycache__/prices.csv"
        with open(f_path, "w") as f:
            f.write(content)

        with open(f_path) as csvfile:
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader):
                if ozon_product := self.is_ozon_product_exists(
                    id_on_platform=row["id_on_platform"]
                ):
                    ozon_product.write(
                        {
                            "price": row["price"],
                            "old_price": row["old_price"],
                            "ext_comp_min_price": row["ext_comp_min_price"],
                            "ozon_comp_min_price": row["ozon_comp_min_price"],
                            "self_marketplaces_min_price": row[
                                "self_marketplaces_min_price"
                            ],
                            "price_index": row["price_index"],
                        }
                    )
                    print(f"{i} - Product {row['id_on_platform']} prices were updated")

        os.remove(f_path)

    def get_or_create_warehouse(self, warehouse_id, warehouse_name):
        """Returns existing warehouse or create a new one"""
        if warehouse := self.env["ozon.warehouse"].search(
            [("w_id", "=", warehouse_id)]
        ):
            pass
        else:
            warehouse = self.env["ozon.warehouse"].create(
                {"name": warehouse_name, "w_id": warehouse_id}
            )
        return warehouse

    def import_postings(self, content):
        f_path = "/mnt/extra-addons/ozon/__pycache__/postings.csv"
        with open(f_path, "w") as f:
            f.write(content)

        with open(f_path) as csvfile:
            reader = csv.DictReader(csvfile)
            data = []
            for i, row in enumerate(reader):
                posting_number = row["posting_number"]
                status = row["status"]
                if self.env["ozon.posting"].search(
                    [("posting_number", "=", posting_number), ("status", "=", status)]
                ):
                    continue
                """
                Создаем отправление только если хотя бы один из товаров в отправлении
                соответствует нашему товару
                """
                skus = ast.literal_eval(row["skus"])
                product_ids = []
                for sku in skus:
                    if ozon_product := self.is_ozon_product_exists_by_sku(sku):
                        product_ids.append(ozon_product.id)
                if not product_ids:
                    continue

                warehouse = self.get_or_create_warehouse(
                    warehouse_id=row["warehouse_id"],
                    warehouse_name=row["warehouse_name"],
                )

                data.append(
                    {
                        "posting_number": posting_number,
                        "in_process_at": row["in_process_at"],
                        "trading_scheme": row["trading_scheme"],
                        "order_id": row["order_id"],
                        "status": status,
                        "product_ids": product_ids,
                        "skus": skus,
                        "region": row["region"],
                        "city": row["city"],
                        "warehouse_id": warehouse.id,
                        "cluster_from": row["cluster_from"],
                        "cluster_to": row["cluster_to"],
                    }
                )
                print(f"{i} - Posting {row['posting_number']} was imported")

            self.env["ozon.posting"].create(data)
        os.remove(f_path)

    def import_fbo_supply_orders(self, content):
        f_path = "/mnt/extra-addons/ozon/__pycache__/fbo_supply_orders.csv"
        with open(f_path, "w") as f:
            f.write(content)

        with open(f_path) as csvfile:
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader):
                supply_order_id = row["supply_order_id"]
                if self.env["ozon.fbo_supply_order"].search(
                    [("supply_order_id", "=", supply_order_id)]
                ):
                    continue
                warehouse = self.get_or_create_warehouse(
                    warehouse_id=row["warehouse_id"],
                    warehouse_name=row["warehouse_name"],
                )
                fbo_supply_order_data = {
                    "created_at": row["created_at"],
                    "supply_order_id": supply_order_id,
                    "total_items_count": row["total_items_count"],
                    "total_quantity": row["total_quantity"],
                    "warehouse_id": warehouse.id,
                }
                if row["supply_date"]:
                    fbo_supply_order_data["supply_date"] = row["supply_date"]

                fbo_supply_order = self.env["ozon.fbo_supply_order"].create(
                    fbo_supply_order_data
                )
                items = ast.literal_eval(row["items"])
                fbo_supply_order_product_data = []
                skus = []
                for item in items:
                    sku = item["sku"]
                    if ozon_product := self.is_ozon_product_exists_by_sku(sku):
                        fbo_supply_order_product_data.append(
                            {
                                "fbo_supply_order_id": fbo_supply_order.id,
                                "product_id": ozon_product.id,
                                "qty": item["qty"],
                            }
                        )
                        skus.append(sku)
                fbo_supply_order_products = self.env[
                    "ozon.fbo_supply_order_product"
                ].create(fbo_supply_order_product_data)
                fbo_supply_order.write(
                    {
                        "fbo_supply_order_products_ids": fbo_supply_order_products.ids,
                        "skus": skus,
                    }
                )
                print(f"{i} - Supply order {supply_order_id} was imported")
        os.remove(f_path)

    def create_sale_from_transaction(self, data: dict, products: list, services_cost: float):
        if len(products) == 0:
            return
        # if all products are the same
        product_id = data["products"][0]
        qty = len(data["products"])
        if data["products"].count(product_id) == qty:
            self.env["ozon.sale"].create(
                {
                    "transaction_identifier": data["transaction_id"],
                    "product": product_id, 
                    "product_id_on_platform": products[0].id_on_platform, 
                    "date": data["order_date"], 
                    "qty": qty, 
                    "revenue": data["accruals_for_sale"],
                    "sale_commission": data["sale_commission"],
                    "services_cost": services_cost,
                    "profit": data["amount"]
                }
            )
        # TODO: что делать если разные продукты в одной транзакции? как создавать продажи?

    def import_ad_campgaign_search_promotion_report(self, content):
        f_path = "/mnt/extra-addons/ozon/__pycache__/ad_campgaign_search_promotion_report.csv"
        with open(f_path, "w") as f:
            f.write(content)
        with open(f_path) as csvfile:
            first_row = next(csvfile)
            ad_campaign = first_row[first_row.find("№") + 2 : first_row.find(",")]
            if not ad_campaign.isdigit():
                raise UserError(
                    """Файл должен содержать номер рекламной кампании в первой строке"""
                )
            reader = csv.DictReader(csvfile, delimiter=";")
            if reader.fieldnames != [
                "Дата",
                "ID заказа",
                "Номер заказа",
                "Ozon ID",
                "Ozon ID продвигаемого товара",
                "Артикул",
                "Наименование",
                "Количество",
                "Цена продажи",
                "Стоимость, ₽",
                "Ставка, %",
                "Ставка, ₽",
                "Расход, ₽",
            ]:
                raise UserError(
                    """Неправильный файл. Файл должен содержать столбцы:\n'Дата', 'ID заказа', 'Номер заказа', 'Ozon ID', 'Ozon ID продвигаемого товара', 'Артикул', 'Наименование', 'Количество', 'Цена продажи', 'Стоимость, ₽', 'Ставка, %', 'Ставка, ₽', 'Расход, ₽'"""
                )
            promo_type = "search"
            data = []
            for i, row in enumerate(reader):
                sku = row["Ozon ID продвигаемого товара"]
                order_id = row["ID заказа"]
                if self.env["ozon.promotion_expenses"].search(
                    [
                        ("ad_campaign", "=", ad_campaign),
                        ("order_id", "=", order_id),
                    ]
                ):
                    continue
                if ozon_product := self.is_ozon_product_exists_by_sku(sku):
                    if (
                        posting_ids := self.env["ozon.posting"]
                        .search(
                            [
                                ("order_id", "=", order_id),
                            ]
                        )
                        .ids
                    ):
                        pass
                    else:
                        posting_ids = None
                    data.append(
                        {
                            "ad_campaign": ad_campaign,
                            "date": datetime.strptime(row["Дата"], "%d.%m.%Y").date(),
                            "promotion_type": promo_type,
                            "product_id": ozon_product.id,
                            "sku": sku,
                            "order_id": order_id,
                            "posting_ids": posting_ids,
                            "price": row["Цена продажи"].replace(",", "."),
                            "qty": row["Количество"],
                            "total_price": row["Стоимость, ₽"].replace(",", "."),
                            "percent_rate": row["Ставка, %"].replace(",", "."),
                            "abs_rate": row["Ставка, ₽"].replace(",", "."),
                            "expense": row["Расход, ₽"].replace(",", "."),
                        }
                    )
                    print(f"{i} - Product (SKU: {sku}) promotion expenses were added")
            self.env["ozon.promotion_expenses"].create(data)
        os.remove(f_path)

    def import_ozon_realisation_report(self, content):
        with StringIO(content) as jsonfile:
            data = json.load(jsonfile)
            if self.env["ozon.realisation_report"].search([("num", "=", data["header"]["num"])]):
                print(f"""Report №{data["header"]["num"]} already exists""")
                return
            report = self.env["ozon.realisation_report"].create({**data["header"]})
            products_in_report_data = []
            for i, row in enumerate(data["rows"]):
                product_id_on_platform = row.pop("product_id")
                product = self.is_ozon_product_exists(product_id_on_platform)
                if product:
                    products_in_report_data.append({
                        "product_id": product.id,
                        "product_id_on_platform": product_id_on_platform,
                        "realisation_report_id": report.id,
                        **row
                    })
                    print(f"{i} - Product {product_id_on_platform} added to realisation report")
            self.env["ozon.realisation_report_product"].create(products_in_report_data)

    def import_images_sale(self, content):
        model_products = self.env["ozon.products"]

        (
            product_id,
            url_this_year,
            url_last_year,
            data_this_year,
            data_last_year,
        ) = content.split(",")

        record = model_products.search([("id", "=", product_id)])

        record.img_url_sale_this_year = url_this_year
        record.img_url_sale_last_year = url_last_year

        record.img_data_sale_this_year = data_this_year.replace("|", ",")
        record.img_data_sale_last_year = data_last_year.replace("|", ",")

    def import_images_sale_by_week(self, content):
        model_products = self.env["ozon.products"]

        (
            product_id,
            url_two_weeks,
            url_six_weeks,
            url_twelve_weeks,
            data_two_weeks,
            data_six_week,
            data_twelve_week,
        ) = content.split(",")

        record = model_products.search([("id", "=", product_id)])

        record.img_url_sale_two_weeks = url_two_weeks
        record.img_url_sale_six_weeks = url_six_weeks
        record.img_url_sale_twelve_weeks = url_twelve_weeks

        record.img_data_sale_two_weeks = data_two_weeks.replace("|", ",")
        record.img_data_sale_six_weeks = data_six_week.replace("|", ",")
        record.img_data_sale_twelve_weeks = data_twelve_week.replace("|", ",")

    def import_images_competitors_products(self, content):
        model_competitors_products = self.env["ozon.products_competitors"]

        product_id, url, data = content.split(",")

        record = model_competitors_products.search([("id", "=", product_id)])
        record.imgs_url_this_year = url
        record.imgs_data_graph_this_year = data.replace("|", ",")

    def import_images_price_history(self, content):
        model_products = self.env["ozon.products"]

        product_id, url, data = content.split(",")

        record = model_products.search([("id", "=", product_id)])

        record.img_url_price_history = url
        record.img_data_price_history = data.replace("|", ",")

    def import_images_stock(self, content):
        model_products = self.env["ozon.products"]

        product_id, url, data = content.split(",")

        record = model_products.search([("id", "=", product_id)])

        record.img_url_stock = url
        record.img_data_stock = data.replace("|", ",")

    def import_images_analysis_data(self, content):
        model_products = self.env["ozon.products"]

        product_id, url, hits_view, hits_tocart = content.split(",")

        record = model_products.search([("id", "=", product_id)])

        record.img_url_analysis_data = url
        record.img_data_analysis_data = {
            "hits_view": hits_view,
            "hits_tocart": hits_tocart,
        }

    def import_images_categorie_analysis_data(self, content):
        model_categories = self.env["ozon.categories"]

        model, categories_id, url, data_hits, data_tocart = content.split(",")
        data_hits = data_hits.replace("|", ",").replace("'", '"')
        data_tocart = data_tocart.replace("|", ",").replace("'", '"')

        record = model_categories.search([("id", "=", categories_id)])

        record.img_url_analysis_data_this_year = url
        record.img_data_analysis_data_this_year = {
            "hits_view": json.loads(data_hits),
            "hits_tocart": json.loads(data_tocart),
        }

    def import_images_categorie_categorie_sale_this_year(self, content):
        model_categories = self.env["ozon.categories"]

        model, categories_id, url, average_data = content.split(",")
        average_data = average_data.replace("|", ",")

        record = model_categories.search([("id", "=", categories_id)])

        record.img_url_sale_this_year = url
        record.img_data_sale_this_year = average_data

    def import_images_categorie_categorie_sale_last_year(self, content):
        model_categories = self.env["ozon.categories"]

        model, categories_id, url, average_data = content.split(",")
        average_data = average_data.replace("|", ",")

        record = model_categories.search([("id", "=", categories_id)])

        record.img_url_sale_last_year = url
        record.img_data_sale_last_year = average_data

    def import_actions(self, content):
        f_path = "/mnt/extra-addons/ozon/__pycache__/actions.csv"
        with open(f_path, "w") as f:
            f.write(content)

        with open(f_path) as csvfile:
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader):
                a_id = row["action_id"]
                is_participating = ast.literal_eval(row["is_participating"])
                potential_prod_count = row["potential_products_count"]
                participating_products_count = row["participating_products_count"]
                if action := self.env["ozon.action"].search([("a_id", "=", a_id)]):
                    action.write(
                        {
                            "is_participating": is_participating,
                            "participating_products_count": participating_products_count,
                        }
                    )
                else:
                    datetime_start = convert_ozon_datetime_str_to_odoo_datetime_str(
                        row["date_start"]
                    )
                    datetime_end = convert_ozon_datetime_str_to_odoo_datetime_str(
                        row["date_end"]
                    )
                    action = self.env["ozon.action"].create(
                        {
                            "a_id": a_id,
                            "name": row["name"],
                            "with_targeting": row["with_targeting"],
                            "datetime_start": datetime_start,
                            "datetime_end": datetime_end,
                            "description": row["description"],
                            "action_type": row["action_type"],
                            "discount_type": row["discount_type"],
                            "discount_value": row["discount_value"],
                            "potential_products_count": potential_prod_count,
                            "is_participating": is_participating,
                            "participating_products_count": participating_products_count,
                        }
                    )

                    candidates = json.loads(row["action_candidates"])
                    candidates_data = []
                    len_candidates = len(candidates)
                    ids_on_platform = []
                    for idx, can in enumerate(candidates):
                        id_on_platform = can["id"]
                        if ozon_product := self.is_ozon_product_exists(id_on_platform):
                            candidates_data.append(
                                {
                                    "action_id": action.id,
                                    "product_id": ozon_product.id,
                                    "id_on_platform": id_on_platform,
                                    "max_action_price": can["max_action_price"],
                                }
                            )
                            ids_on_platform.append(id_on_platform)
                            print(
                                f"{idx}/{len_candidates} - Product {id_on_platform} was added as action {a_id} candidate"
                            )

                    action_candidate_ids = (
                        self.env["ozon.action_candidate"].create(candidates_data).ids
                    )
                    action.write(
                        {
                            "action_candidate_ids": action_candidate_ids,
                            "ids_on_platform": ids_on_platform,
                        }
                    )

                if is_participating:
                    participants = json.loads(row["action_participants"])
                    for par in participants:
                        id_on_platform = str(par["id_on_platform"])
                        action_candidate = action.action_candidate_ids.filtered(
                            lambda r: r.product_id_on_platform == id_on_platform
                        )
                        if action_candidate:
                            action_candidate.is_participating = True

                print(f"{i} - Action {a_id} was imported")

        os.remove(f_path)

    def import_successful_products_competitors(self, content):
        lines = content.split("\n")

        for line in lines[1:]:
            if not line:
                continue

            sku, name = line.split(",")

            model_successful_products_competitors = self.env[
                "ozon.successful_product_competitors"
            ]
            model_successful_products_competitors.create(
                {
                    "sku": sku,
                    "name": name,
                }
            )

    def _parse_ozon_competitors_goods_xlsx_file(self, wb):
        for sheet in wb.worksheets:
            period_from = None
            period_to = None
            category = None

            # get period and category via parsing
            for row in sheet.iter_rows(min_row=1, max_row=4, values_only=True):
                if row[0]:
                    if "Период:" in row[0]:
                        splited_row = row[0].split(" ")
                        for str_ in splited_row:
                            if str_[0].isnumeric() and not period_from:
                                period_from = date(*[int(x) for x in str_.split("-")])
                                continue
                            if str_[0].isnumeric() and period_from and not period_to:
                                period_to = date(*[int(x) for x in str_.split("-")])
                                break
                    elif "Категория:" in row[0]:
                        splited_row = row[0].split(": ")
                        category = splited_row[1]

            # create report
            existed_category = self.env["ozon.categories"].search(
                [("name_categories", "=", category)]
            )
            report = self.env["ozon.report_category_market_share"].create(
                {
                    "ozon_categories_id": existed_category.id if existed_category else False,
                    "period_from": period_from,
                    "period_to": period_to,
                }
            )

            # accumulate data from file
            sellers_cache = defaultdict(lambda: None)
            competitors_sales_ids = []
            sales_and_share_per_seller = defaultdict(int)
            for row in sheet.iter_rows(
                min_row=4, max_col=8, max_row=sheet.max_row, values_only=True
            ):
                if row[0] and row[0] != "№":
                    competitor_name = row[1]
                    product_name = row[2]
                    article = row[3]
                    category_lvl2 = row[4]
                    category_lvl3 = row[5]
                    ordered_quantity = row[6]
                    ordered_amount = row[7]

                    # get seller
                    seller = sellers_cache.get(competitor_name)
                    if not seller:
                        seller = self._get_seller(competitor_name)
                        sellers_cache[competitor_name] = seller

                    product_competitor_or_product = (
                        self._get_product_competitor_or_product(article, seller)
                    )
                    sales_and_share_per_seller[seller] += ordered_amount

                    competitor_sale = self._get_competitor_sale(
                        product_competitor_or_product,
                        period_from,
                        period_to,
                        ordered_quantity,
                        ordered_amount,
                        category_lvl3,
                        seller,
                        product_name,
                        article,
                    )
                    competitors_sales_ids.append(competitor_sale.id)

            # create ozon.report.competitor_category_share
            sellers = [
                (seller, shares)
                for seller, shares in sales_and_share_per_seller.items()
            ]
            sellers.sort(key=lambda x: x[1], reverse=True)
            place = 1
            competitors_category_share_ids = []
            for seller_tuple in sellers:
                competitor_category_share = self.env[
                    "ozon.report.competitor_category_share"
                ].create(
                    {
                        "place": place,
                        "seller_name": seller_tuple[0].trade_name,
                        "turnover": seller_tuple[1],
                    }
                )
                competitors_category_share_ids.append(competitor_category_share.id)
                place += 1

            # add data to report
            report.ozon_products_competitors_sale_ids = competitors_sales_ids
            report.ozon_report_competitor_category_share_ids = (
                competitors_category_share_ids
            )

        wb.close()

    def _get_competitor_sale(
        self,
        product_competitor_or_product,
        period_from,
        period_to,
        ordered_quantity,
        ordered_amount,
        category_lvl3,
        seller,
        product_name,
        article,
    ):
        competitor_sale = None
        if not seller.is_my_shop:
            if product_competitor_or_product:
                for (
                    sale
                ) in product_competitor_or_product.ozon_products_competitors_sale_ids:
                    if (
                        sale.period_from == period_from
                        and sale.period_to == period_to
                        and sale.seller_name == seller.trade_name
                    ):
                        sale.orders_qty = ordered_quantity
                        sale.orders_sum = ordered_amount
                        competitor_sale = sale
            if not competitor_sale:
                competitor_sale = self.env["ozon.products_competitors.sale"].create(
                    {
                        "period_from": period_from,
                        "period_to": period_to,
                        "ozon_products_competitors_id": (
                            product_competitor_or_product.id
                            if product_competitor_or_product
                            else False
                        ),
                        "orders_qty": ordered_quantity,
                        "orders_sum": ordered_amount,
                        "category_lvl3": category_lvl3,
                        "seller_name": seller.trade_name,
                        "name": f"{article}, {product_name}",
                    }
                )
        else:
            competitor_sale = self.env["ozon.products_competitors.sale"].create(
                {
                    "period_from": period_from,
                    "period_to": period_to,
                    "ozon_products_id": product_competitor_or_product.id,
                    "orders_qty": ordered_quantity,
                    "orders_sum": ordered_amount,
                    "category_lvl3": category_lvl3,
                    "seller_name": seller.trade_name,
                    "name": f"{article}, {product_name}",
                }
            )

        return competitor_sale

    def _get_product_competitor_or_product(self, article, seller) -> Any:
        if seller.is_my_shop:
            product = self.env["ozon.products"].search(
                [
                    ("article", "=", article),
                    # ('seller', '=', seller.id),
                ],
                limit=1,
            )
            if not product:
                pass
            return product
        else:
            product_competitor = self.env["ozon.products_competitors"].search(
                [
                    ("article", "=", article),
                    ("competitor_seller_id", "=", seller.id),
                ],
                limit=1,
            )

            return product_competitor

    def _get_seller(self, competitor_name: str) -> Any:
        seller = self.env["ozon.competitor_seller"].search(
            [("trade_name", "=", competitor_name)], limit=1
        )
        if not seller:
            seller = self.env["retail.seller"].search(
                [("trade_name", "=", competitor_name)], limit=1
            )
        if not seller:
            seller = self.env["ozon.competitor_seller"].create(
                {"trade_name": competitor_name}
            )

        return seller
