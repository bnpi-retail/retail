import ast
import base64
import csv
import os
from uu import Error
import magic
import xml.etree.ElementTree as ET

from io import StringIO
from odoo import models, fields, api, exceptions

from ..controllers.ozon_api import (
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

    data_for_download = fields.Selection(
        [
            ("index_local", "Индекс локализации"),
            ("logistics_cost", "Стоимость логистики"),
            ("fees", "Комиссии"),
            ("excel_fbo", "Excel FBO"),
            ("excel_fbs", "Excel FBS"),
            ("fee_fix", "Excel Fix"),
            ("ozon_products", "Товары Ozon"),
            ("ozon_products_api", "Товары Ozon API"),
            ("ozon_commissions", "Комиссии Ozon по категориям"),
            ("ozon_transactions", "Транзакции Ozon"),
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

        #############################
        ##### API OZON TEMPORAL #####
        #############################
        
        if values["data_for_download"] == "ozon_products_api":
            uploaded_file = values['file']
            csv_data = uploaded_file.read().decode('utf-8')
            values['file'] = csv_data

            decoded_data = base64.b64decode(csv_data).decode('utf-8')

            csv_reader = csv.reader(StringIO(decoded_data))

            header = "categories,id_on_platform,full_categories,name,description,product_id,length,width,height,weight,seller_name,lower_threshold,upper_threshold,coefficient,percent,trading_scheme,delivery_location,price,acquiring,fbo_fulfillment_amount,fbo_direct_flow_trans_min_amount,fbo_direct_flow_trans_max_amount,fbo_deliv_to_customer_amount,fbo_return_flow_amount,fbo_return_flow_trans_min_amount,fbo_return_flow_trans_max_amount,fbs_first_mile_min_amount,fbs_first_mile_max_amount,fbs_direct_flow_trans_min_amount,fbs_direct_flow_trans_max_amount,fbs_deliv_to_customer_amount,fbs_return_flow_amount,fbs_return_flow_trans_min_amount,fbs_return_flow_trans_max_amount,sales_percent_fbo,sales_percent_fbs,sales_percent"
            headers = header.split(',')

            for row in csv_reader:
                row = dict(zip(headers, row))

                try:
                    if ozon_product := self.is_ozon_product_exists(
                        id_on_platform=row["id_on_platform"],
                        trading_scheme=row["trading_scheme"],
                    ):
                        pass
                except KeyError as e:
                    print(f'OZON Error ozon_product {e},\n {row}')
                    continue


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
                    try:
                        if localization_index := self.is_ozon_localization_index_exists(
                            row["lower_threshold"],
                            row["upper_threshold"],
                            row["coefficient"],
                            row["percent"],
                        ):
                            pass
                    except ValueError as e:
                        print(f'OZON Error localization_index {e}')
                        continue

                    else:
                        try:
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
                        except ValueError as e:
                            print(f'OZON Error localization_index {e}')
                            continue
                    try:
                        retail_product = self.env["retail.products"].create(
                            {
                                "name": row["name"],
                                "description": row["description"],
                                "product_id": row["product_id"],
                                "length": float(row["length"]),
                                "width": float(row["width"]),
                                "height": float(row["height"]),
                                "weight": float(row["weight"]),
                            }
                        )
                    except ValueError as e:
                        print(f'OZON Error localization_index {e}')
                        continue
                    try:
                        ozon_product = self.env["ozon.products"].create(
                            {
                                "categories": ozon_category.id,
                                "id_on_platform": row["id_on_platform"],
                                "full_categories": row["full_categories"],
                                "products": retail_product.id,
                                "seller": seller.id,
                                "index_localization": localization_index.id,
                                "trading_scheme": row["trading_scheme"],
                                "delivery_location": row["delivery_location"],
                            }
                        )
                        print(f"product {row['id_on_platform']} created")
                    except ValueError as e:
                        print(f'OZON Error localization_index {e}')
                        continue
                
                if row["trading_scheme"] == "FBO":
                    fix_coms_by_trad_scheme = FBO_FIX_COMMISSIONS
                    percent_coms_by_trad_scheme = FBO_PERCENT_COMMISSIONS
                elif row["trading_scheme"] == "FBS":
                    fix_coms_by_trad_scheme = FBS_FIX_COMMISSIONS
                    percent_coms_by_trad_scheme = FBS_PERCENT_COMMISSIONS
                elif row["trading_scheme"] == "":
                    fix_coms_by_trad_scheme = None
                    percent_coms_by_trad_scheme = None
            
                try:
                    ozon_price_history_data = {
                        "product": ozon_product.id,
                        "provider": ozon_product.seller.id,
                        "price": float(row["price"]),
                    }
                except ValueError as e:
                    print(f'OZON Error ozon_price_history_data {e}')

                if fix_coms_by_trad_scheme:
                    fix_product_commissions = {
                        k: row[k] for k in fix_coms_by_trad_scheme
                    }
                    fix_expenses = []
                    for com, value in fix_product_commissions.items():
                        fix_expenses_record = self.env[
                            "ozon.fix_expenses"
                        ].create(
                            {
                                "name": fix_coms_by_trad_scheme[com],
                                "price": value,
                                "discription": "",
                            }
                        )
                        fix_expenses.append(fix_expenses_record.id)

                    ozon_price_history_data["fix_expensives"] = fix_expenses

                if percent_coms_by_trad_scheme:
                    percent_product_commissions = {
                        k: row[k] for k in percent_coms_by_trad_scheme
                    }
                    costs = []
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
            return super(ImportFile, self).create(values)

        ###################
        ##### ANOTHER #####
        ###################
        content = base64.b64decode(values["file"])
        mime_type = self.get_file_mime_type(content)
        mime_type = mime_type.lower()
        format = mime_type

        try:
            root = ET.fromstring(content)

            logistics_ozon = self.env["ozon.logistics_ozon"]

            if values["data_for_download"] == "excel_fbo":
                logistics_ozon = self.env["ozon.logistics_ozon"]

                for entry in root.findall("entry"):
                    volume = entry.find("volume").text
                    rate = entry.find("rate").text

                    logistics_ozon.create(
                        {
                            "trading_scheme": "FBO",
                            "volume": volume,
                            "price": rate,
                        }
                    )

            elif values["data_for_download"] == "excel_fbs":
                logistics_ozon = self.env["ozon.logistics_ozon"]

                for entry in root.findall("entry"):
                    volume = entry.find("volume").text
                    rate = entry.find("rate").text

                    logistics_ozon.create(
                        {
                            "trading_scheme": "FBS",
                            "volume": volume,
                            "price": rate,
                        }
                    )

            elif values["data_for_download"] == "fee_fix":
                ozon_fee = self.env["ozon.ozon_fee"]

                for entry in root.findall("entry"):
                    ppt = entry.find("PPT").text
                    volume = entry.find("volume").text

                    if ppt == "ППЗ":
                        ppt_in_selections = "PC"
                    elif ppt == "ПВЗ":
                        ppt_in_selections = "PP"
                    elif ppt == "СЦ":
                        ppt_in_selections = "SC"
                    elif ppt == "ТСЦ":
                        ppt_in_selections = "TSC"

                    ozon_fee.create(
                        {
                            # 'name': categorie.id,
                            "value": volume,
                            # 'category': categorie.id,
                            "type": "fix",
                            "delivery_location": ppt_in_selections,
                        }
                    )

            elif values["data_for_download"] == "fees":
                ozon_fee = self.env["ozon.ozon_fee"]
                categories = self.env["ozon.categories"]

                for category in root.findall("Category"):
                    name = category.find("Name").text
                    fbo_commission = category.find("FBO_Commission").text.replace(
                        "%", ""
                    )
                    fbs_commission = category.find("FBS_Commission").text.replace(
                        "%", ""
                    )
                    rfbs_commission = category.find("RFBS_Commission").text.replace(
                        "%", ""
                    )
                    fbo_last_mile_percentage = (
                        category.find("FBO_Last_Mile_Percentage").text
                        if category.find("FBO_Last_Mile_Percentage") is not None
                        else ""
                    )
                    fbo_last_mile_min = (
                        category.find("FBO_Last_Mile_Min").text
                        if category.find("FBO_Last_Mile_Min") is not None
                        else ""
                    )

                    categorie = categories.search([("name_categories", "=", name)])

                    value = {
                        "name": name,
                        "value": fbo_commission,
                        "category": categorie.id,
                        "type": "percent",
                        "trading_scheme": "FBO",
                    }
                    if categorie:
                        value["category"] = categorie.id
                    ozon_fee.create(value)

                    value = {
                        "name": name,
                        "value": fbs_commission,
                        "category": categorie.id,
                        "type": "percent",
                        "trading_scheme": "FBS",
                    }
                    if categorie:
                        value["category"] = categorie.id
                    ozon_fee.create(value)

                    value = {
                        "name": name,
                        "value": rfbs_commission,
                        "category": categorie.id,
                        "type": "percent",
                        "trading_scheme": "rFBS",
                    }
                    if categorie:
                        value["category"] = categorie.id
                    ozon_fee.create(value)

            return super(ImportFile, self).create(values)
        except ET.ParseError:
            pass

        content_old = content
        content = content.decode("utf-8")
        lines = content.split("\n")

        if "csv" in mime_type:
            if values["data_for_download"] == "index_local":
                localization_index = self.env["ozon.localization_index"]

                for line in lines:
                    if line:
                        range_str, value_str = line.split(",")
                        range_start, range_end = map(int, range_str.split("-"))
                        value = float(value_str)

                        localization_index.create(
                            {
                                "lower_threshold": range_start,
                                "upper_threshold": range_end,
                                "coefficient": value,
                                "percent": (value - 1) * 100,
                            }
                        )

            elif values["data_for_download"] == "logistics_cost":
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
                            id_on_platform=row["id_on_platform"],
                            trading_scheme=row["trading_scheme"],
                        ):
                            pass

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
                                    "seller": seller.id,
                                    "index_localization": localization_index.id,
                                    "trading_scheme": row["trading_scheme"],
                                    "delivery_location": row["delivery_location"],
                                }
                            )
                            print(f"product {row['id_on_platform']} created")

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

                        if fix_coms_by_trad_scheme:
                            fix_product_commissions = {
                                k: row[k] for k in fix_coms_by_trad_scheme
                            }
                            fix_expenses = []
                            for com, value in fix_product_commissions.items():
                                fix_expenses_record = self.env[
                                    "ozon.fix_expenses"
                                ].create(
                                    {
                                        "name": fix_coms_by_trad_scheme[com],
                                        "price": value,
                                        "discription": "",
                                    }
                                )
                                fix_expenses.append(fix_expenses_record.id)

                            ozon_price_history_data["fix_expensives"] = fix_expenses

                        if percent_coms_by_trad_scheme:
                            percent_product_commissions = {
                                k: row[k] for k in percent_coms_by_trad_scheme
                            }
                            costs = []
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

        if values["data_for_download"] == "excel":
            import xlrd

            content_decoded = content_old.decode("latin-1")
            workbook = xlrd.open_workbook(file_contents=content_decoded)

            sheet = workbook.sheet_by_index(0)

            for row_idx in range(sheet.nrows):
                for col_idx in range(sheet.ncols):
                    cell_value = sheet.cell_value(row_idx, col_idx)
                    print(cell_value)

        return super(ImportFile, self).create(values)

    def is_ozon_product_exists(self, id_on_platform: str, trading_scheme: str):
        result = self.env["ozon.products"].search(
            [
                ("id_on_platform", "=", id_on_platform),
                ("trading_scheme", "=", trading_scheme),
            ],
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
                print("ozon_products ids", ozon_products, row["amount"])
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

        os.remove(f_path)
