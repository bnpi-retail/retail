import ast
import base64
import csv
import os

import magic


from odoo import models, fields, api, exceptions

from ..ozon_api import (
    ALL_COMMISSIONS,
    FBO_FIX_COMMISSIONS,
    FBO_PERCENT_COMMISSIONS,
    FBS_FIX_COMMISSIONS,
    FBS_PERCENT_COMMISSIONS,
)


class ImportFile(models.Model):
    _name = "ozon.import_file"
    _description = "Импорт"
    timestamp = fields.Date(
        string="Дата импорта", default=fields.Date.today, readonly=True
    )
    worker = fields.Char(string="Сотрудник")

    data_for_download = fields.Selection(
        [
            ("logistics_cost", "Стоимость логистики"),
            ("ozon_products", "Товары Ozon"),
            ("ozon_plugin", "Товары Ozon (Плагин)"),
            ("ozon_commissions", "Комиссии Ozon по категориям"),
            ("ozon_transactions", "Транзакции Ozon"),
            ("ozon_stocks", "Остатки товаров Ozon"),
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

        content = base64.b64decode(values["file"])
        mime_type = self.get_file_mime_type(content)
        mime_type = mime_type.lower()

        content = content.decode("utf-8")
        lines = content.split("\n")

        if values["data_for_download"] == "ozon_plugin":
            model_search_queries = self.env["ozon.search_queries"]
            model_products = self.env["ozon.products"]
            model_competitors_products = self.env["ozon.products_competitors"]
            model_analysis_competitors = self.env["ozon.analysis_competitors"]
            model_price_history_competitors = self.env["ozon.price_history_competitors"]
            model_analysis_competitors_record = self.env["ozon.analysis_competitors_record"]

            # Find product from all ads 
            dict_products = {}
            for line in lines[1:]:
                values_list = line.split(",")
                if len(values_list) != 9:
                    continue
                search = values_list[1]
                sku = values_list[3]
                if search not in dict_products:
                    dict_products[search] = {'skus': [], 'products': []}
                dict_products[search]['skus'].append(sku)

            for search in dict_products:
                for sku in dict_products[search]['skus']:
                    record_product = model_products.search([("id_on_platform", "=", str(sku))])
                    if record_product:
                        dict_products[search]['products'].append(record_product.id)

            # Create 
            dict_values = {}
            for line in lines[1:]:
                values_list = line.split(",")
                if len(values_list) != 9:
                    continue

                (
                    number,
                    search,
                    seller,
                    sku,
                    price,
                    price_without_sale,
                    price_with_card,
                    href,
                    name,
                ) = values_list

                record_search = model_search_queries.search([("words", "=", search)])

                if record_search:
                    search_reference = record_search.id
                else:
                    record_search = model_search_queries.create({"words": search})
                    search_reference = record_search.id

                if search_reference not in dict_values:
                    dict_values[search_reference] = []

                record_product = model_products.search(
                    [("id_on_platform", "=", str(sku))]
                )
                if record_product:
                    ad_reference = "ozon.products," + str(record_product.id)
                    is_my_product = True

                else:
                    is_my_product = False
                    record_competitors_products = model_competitors_products.search(
                        [("id_product", "=", str(sku))]
                    )
                    if record_competitors_products:
                        ad_reference = "ozon.products_competitors," + str(
                            record_competitors_products.id
                        )
                    else:
                        try:
                            product_id = dict_products[search]['products'][0]
                        except Exception as e:
                            product_id = None
                        if product_id:
                            record_competitors_products = model_competitors_products.create({
                                "id_product": str(sku),
                                "name": str(name),
                                "url": str(href),
                                "product": product_id,
                            })
                        else:
                            record_competitors_products = model_competitors_products.create({
                                "id_product": str(sku),
                                "name": str(name),
                                "url": str(href),
                            })
                        ad_reference = "ozon.products_competitors," + str(
                            record_competitors_products.id
                        )

                record_data = {}
                record_price_history_competitors = {}
                if is_my_product != "None":
                    record_data["is_my_product"] = is_my_product
                if number != "None":
                    record_data["number"] = number
                if name != "None":
                    record_data["name"] = name
                if price != "None":
                    record_data["price"] = price
                    record_price_history_competitors["price"] = price
                if price_without_sale != "None":
                    record_data["price_without_sale"] = price_without_sale
                    record_price_history_competitors["price_without_sale"] = price_without_sale
                if price_with_card != "None":
                    record_data["price_with_card"] = price_with_card
                    record_price_history_competitors["price_with_card"] = price_with_card
                if ad_reference != "None":
                    record_data["ad"] = ad_reference
                record = model_analysis_competitors_record.create(record_data)

                if record_competitors_products:
                    record_price_history_competitors["product_competitors"] = record_competitors_products.id
                if record_competitors_products.product_id:
                    record_price_history_competitors["product_id"] = record_competitors_products.product_id
                    

                model_price_history_competitors.create(record_price_history_competitors)
                dict_values[search_reference].append(record.id)

            for search_id, ids in dict_values.items():
                model_analysis_competitors.create({
                    "worker": values["worker"],
                    "search_query": search_id,
                    "competitor_record": [(6, 0, ids)],
                })

        if "csv" in mime_type:
            if values["data_for_download"] == "logistics_cost":
                logistics_ozon = self.env["ozon.logistics_ozon"]

                for line in lines:
                    if line:
                        trading_scheme, volume, price = line.split(",")
                        volume = float(volume)
                        price = float(price)

                        logistics_ozon.create(
                            {
                                "trading_scheme": trading_scheme,
                                "volume": volume,
                                "price": price,
                            }
                        )

            elif values["data_for_download"] == "ozon_products":
                f_path = "/mnt/extra-addons/ozon/products_from_ozon_api.csv"
                with open(f_path, "w") as f:
                    f.write(content)

                with open(f_path) as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        if ozon_product := self.is_ozon_product_exists(
                            id_on_platform=row["id_on_platform"]
                        ):
                            retail_product = self.is_retail_product_exists(
                                product_id=row["product_id"]
                            )
                            retail_product.write(
                                {
                                    "name": row["name"],
                                    "description": row["description"],
                                    "keywords": row["keywords"],
                                }
                            )

                        else:
                            if ozon_category := self.is_ozon_category_exists(
                                row["categories"]
                            ):
                                pass
                            else:
                                ozon_category = self.env["ozon.categories"].create(
                                    {"name_categories": row["categories"]}
                                )
                            if seller := self.is_retail_seller_exists(
                                row["seller_name"]
                            ):
                                pass
                            else:
                                seller = self.env["retail.seller"].create(
                                    {
                                        "name": "Продавец",
                                        "ogrn": 1111111111111,
                                        "fee": 20,
                                    }
                                )
                            if localization_index := self.is_ozon_localization_index_exists(
                                row["lower_threshold"],
                                row["upper_threshold"],
                                row["coefficient"],
                                row["percent"],
                            ):
                                pass
                            else:
                                localization_index = self.env[
                                    "ozon.localization_index"
                                ].create(
                                    {
                                        "lower_threshold": float(
                                            row["lower_threshold"]
                                        ),
                                        "upper_threshold": float(
                                            row["upper_threshold"]
                                        ),
                                        "coefficient": float(row["coefficient"]),
                                        "percent": float(row["percent"]),
                                    }
                                )

                            retail_product = self.env["retail.products"].create(
                                {
                                    "name": row["name"],
                                    "description": row["description"],
                                    "keywords": row["keywords"],
                                    "product_id": row["product_id"],
                                    "length": float(row["length"]),
                                    "width": float(row["width"]),
                                    "height": float(row["height"]),
                                    "weight": float(row["weight"]),
                                }
                            )

                            ozon_product = self.env["ozon.products"].create(
                                {
                                    "categories": ozon_category.id,
                                    "id_on_platform": row["id_on_platform"],
                                    "full_categories": row["full_categories"],
                                    "products": retail_product.id,
                                    "price": row["price"],
                                    "seller": seller.id,
                                    "index_localization": localization_index.id,
                                    "trading_scheme": row["trading_scheme"],
                                    "delivery_location": row["delivery_location"],
                                }
                            )

                            print(f"product {row['id_on_platform']} created")

                        ozon_product.populate_search_queries(row["keywords"])

                        # all_fees = {k: row[k] for k in ALL_COMMISSIONS.keys()}
                        # if product_fee := self.is_product_fee_exists(ozon_product):
                        #     product_fee.write({"product": ozon_product.id, **all_fees})
                        # else:
                        #     product_fee = self.env["ozon.product_fee"].create(
                        #         {"product": ozon_product.id, **all_fees}
                        #     )
                        #     ozon_product.write(
                        #         values={"product_fee": product_fee},
                        #         cr=ozon_product,
                        #     )

                        if row["trading_scheme"] == "FBO":
                            fix_coms_by_trad_scheme = FBO_FIX_COMMISSIONS
                            percent_coms_by_trad_scheme = FBO_PERCENT_COMMISSIONS
                        elif row["trading_scheme"] == "FBS":
                            fix_coms_by_trad_scheme = FBS_FIX_COMMISSIONS
                            percent_coms_by_trad_scheme = FBS_PERCENT_COMMISSIONS
                        elif row["trading_scheme"] == "":
                            fix_coms_by_trad_scheme = None
                            percent_coms_by_trad_scheme = None

                        prev_price_history_record = self.is_ozon_price_history_exists(
                            row["id_on_platform"]
                        )
                        if prev_price_history_record:
                            previous_price = prev_price_history_record.price
                        else:
                            previous_price = 0

                        ozon_price_history_data = {
                            "product": ozon_product.id,
                            "provider": ozon_product.seller.id,
                            "price": float(row["price"]),
                            "previous_price": previous_price,
                        }

                        fix_expenses = []
                        if fix_coms_by_trad_scheme:
                            fix_product_commissions = {
                                k: row[k] for k in fix_coms_by_trad_scheme
                            }
                            for com, value in fix_product_commissions.items():
                                fix_expenses_record = self.env[
                                    "ozon.fix_expenses"
                                ].create(
                                    {
                                        "name": fix_coms_by_trad_scheme[com],
                                        "price": value,
                                        "discription": "",
                                        "product_id": ozon_product.id,
                                    }
                                )
                                fix_expenses.append(fix_expenses_record.id)

                            ozon_price_history_data["fix_expenses"] = fix_expenses
                            ozon_product.write(
                                {"fix_expenses": fix_expenses},
                                cr=ozon_product,
                            )

                        costs = []
                        if percent_coms_by_trad_scheme:
                            ozon_product.percent_expenses.search(
                                [
                                    ("product_id", "=", ozon_product.id),
                                    (
                                        "name",
                                        "in",
                                        [
                                            "Процент комиссии за продажу (FBO)",
                                            "Процент комиссии за продажу (FBS)",
                                        ],
                                    ),
                                ]
                            ).unlink()
                            percent_product_commissions = {
                                k: row[k] for k in percent_coms_by_trad_scheme
                            }
                            for com, value in percent_product_commissions.items():
                                abs_com = round(
                                    ozon_price_history_data["price"]
                                    * float(value)
                                    / 100,
                                    2,
                                )
                                costs_record = self.env["ozon.cost"].create(
                                    {
                                        "name": percent_coms_by_trad_scheme[com],
                                        "price": abs_com,
                                        "discription": f"{value}%",
                                        "product_id": ozon_product.id,
                                    }
                                )
                                costs.append(costs_record.id)

                            ozon_price_history_data["costs"] = costs

                        ozon_price_history = self.env["ozon.price_history"].create(
                            ozon_price_history_data
                        )

                        print(
                            f"price history for product {row['id_on_platform']} added"
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

                        if ozon_category := self.is_ozon_category_exists(
                            row["category_name"]
                        ):
                            pass
                        else:
                            ozon_category = self.env["ozon.categories"].create(
                                {"name_categories": row["category_name"]}
                            )

                        self.env["ozon.ozon_fee"].create(
                            {
                                "name": row["commission_name"],
                                "value": row["value"],
                                "category": ozon_category.id,
                                "type": row["commission_type"],
                                "trading_scheme": row["trading_scheme"],
                                "delivery_location": row["delivery_location"],
                            }
                        )
                        print(f"{i}th commission was created")

                os.remove(f_path)

            elif values["data_for_download"] == "ozon_transactions":
                self.import_transactions(content)

            elif values["data_for_download"] == "ozon_stocks":
                self.import_stocks(content)

        return super(ImportFile, self).create(values)

    def is_ozon_product_exists(self, id_on_platform: str):
        result = self.env["ozon.products"].search(
            [("id_on_platform", "=", id_on_platform)],
            limit=1,
        )
        return result if result else False

    def get_ozon_product_by_id_on_platform(self, id_on_platform: str):
        result = self.env["ozon.products"].search(
            [
                ("id_on_platform", "=", id_on_platform),
            ],
            limit=1,
        )
        return result if result else False

    def is_ozon_category_exists(self, category_name):
        result = self.env["ozon.categories"].search(
            [("name_categories", "=", category_name)],
            limit=1,
        )
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

    def is_ozon_localization_index_exists(
        self, l_threshold, u_threshold, coef, percent
    ):
        result = self.env["ozon.localization_index"].search(
            [
                ("lower_threshold", "=", l_threshold),
                ("upper_threshold", "=", u_threshold),
                ("coefficient", "=", coef),
                ("percent", "=", percent),
            ],
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

    def is_ozon_price_history_exists(self, product_id_on_platform):
        """Ищет последнюю запись истории цен по данному ozon.product.id_on_platform"""
        result = self.env["ozon.price_history"].search(
            [
                ("product.id_on_platform", "=", product_id_on_platform),
            ],
            order="create_date desc",
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
        )
        return result if result else False

    def import_transactions(self, content):
        f_path = "/mnt/extra-addons/ozon/__pycache__/transactions.csv"
        with open(f_path, "w") as f:
            f.write(content)

        with open(f_path) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if self.is_ozon_transaction_exists(
                    transaction_id=row["transaction_id"]
                ):
                    continue
                ozon_products = []
                prod_ids_list = ast.literal_eval(row["product_ids_on_platform"])
                for prod_id in prod_ids_list:
                    ozon_product = self.get_ozon_product_by_id_on_platform(
                        id_on_platform=prod_id
                    )
                    if ozon_product:
                        ozon_products.append(ozon_product.id)

                if len(prod_ids_list) != len(ozon_products):
                    continue

                ozon_services = []
                service_list = ast.literal_eval(row["services"])
                for name, price in service_list:
                    service = self.env["ozon.ozon_services"].create(
                        {"name": name, "price": price}
                    )
                    ozon_services.append(service.id)
                data = {
                    "transaction_id": str(row["transaction_id"]),
                    "transaction_date": row["transaction_date"],
                    "order_date": row["order_date"],
                    "name": row["name"],
                    "amount": row["amount"],
                    "products": ozon_products,
                    "services": ozon_services,
                    "posting_number": row["posting_number"],
                }
                ozon_transaction = self.env["ozon.transaction"].create(data)
                print(f"Transaction {row['transaction_id']} was created")
                # creating ozon.sale records
                if row["name"] == "Доставка покупателю":
                    self.create_sale_from_transaction(
                        products=ozon_products,
                        date=row["order_date"],
                        revenue=row["amount"],
                    )

        os.remove(f_path)

    def import_stocks(self, content):
        f_path = "/mnt/extra-addons/ozon/__pycache__/stocks.csv"
        with open(f_path, "w") as f:
            f.write(content)

        with open(f_path) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if ozon_product := self.is_ozon_product_exists(
                    id_on_platform=row["id_on_platform"]
                ):
                    if stock := self.is_stock_exists(ozon_product.id):
                        stock.write(
                            {
                                "stocks_fbs": row["stocks_fbs"],
                                "stocks_fbo": row["stocks_fbo"],
                            }
                        )
                        print(f"Product {row['id_on_platform']} stocks were updated")
                    else:
                        stock = self.env["ozon.stock"].create(
                            {
                                "product": ozon_product.id,
                                "stocks_fbs": row["stocks_fbs"],
                                "stocks_fbo": row["stocks_fbo"],
                                "_prod_id": row["product_id"],
                            }
                        )
                        print(f"Product {row['id_on_platform']} stocks were created")

                    ozon_product.write({"stock": stock.id}, cr=ozon_product)

        os.remove(f_path)

    def is_retail_cost_price_exists(self, ozon_product):
        result = self.env["retail.cost_price"].search(
            [("products", "=", ozon_product.products.id)],
            order="timestamp desc",
            limit=1,
        )
        return result if result else False

    def is_product_fee_exists(self, ozon_product):
        result = self.env["ozon.product_fee"].search(
            [("product.id", "=", ozon_product.id)],
            limit=1,
        )
        return result if result else False

    def create_sale_from_transaction(self, products: list, date: str, revenue: float):
        # if all products are the same
        product = products[0]
        qty = len(products)
        if products.count(product) == qty:
            self.env["ozon.sale"].create(
                {"product": product, "date": date, "qty": qty, "revenue": revenue}
            )

        # TODO: different products in one transaction
