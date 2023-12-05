import csv
import json

import os
from pprint import pprint as pp
import requests

OZON_CLIENT_ID = os.getenv("OZON_CLIENT_ID")
OZON_API_KEY = os.getenv("OZON_API_KEY")

if not OZON_CLIENT_ID or not OZON_API_KEY:
    raise ValueError("Env variables $OZON_CLIENT_ID and $OZON_API_KEY weren't found")

headers = {
    "Client-Id": OZON_CLIENT_ID,
    "Api-Key": OZON_API_KEY,
}

attributes_ids = {
    "категория": 9461,
    "артикул продавца": 9024,
    "родительская категория": 22387,
    "name": 4180,
    "description": 4191,
}


COMMISSIONS = {
    "acquiring": "Максимальная комиссия за эквайринг",
    "fbo_fulfillment_amount": "Комиссия за сборку заказа (FBO)",
    "fbo_direct_flow_trans_min_amount": "Магистраль от (FBO)",
    "fbo_direct_flow_trans_max_amount": "Магистраль до (FBO)",
    "fbo_deliv_to_customer_amount": "Последняя миля (FBO)",
    "fbo_return_flow_amount": "Комиссия за возврат и отмену (FBO)",
    "fbo_return_flow_trans_min_amount": "Комиссия за обратную логистику от (FBO)",
    "fbo_return_flow_trans_max_amount": "Комиссия за обратную логистику до (FBO)",
    "fbs_first_mile_min_amount": "Минимальная комиссия за обработку отправления (FBS) — 0 рублей",
    "fbs_first_mile_max_amount": "Максимальная комиссия за обработку отправления (FBS) — 25 рублей",
    "fbs_direct_flow_trans_min_amount": "Магистраль от (FBS)",
    "fbs_direct_flow_trans_max_amount": "Магистраль до (FBS)",
    "fbs_deliv_to_customer_amount": "Последняя миля (FBS)",
    "fbs_return_flow_amount": "Комиссия за возврат и отмену, обработка отправления (FBS)",
    "fbs_return_flow_trans_min_amount": "Комиссия за возврат и отмену, магистраль от (FBS)",
    "fbs_return_flow_trans_max_amount": "Комиссия за возврат и отмену, магистраль до (FBS)",
    "sales_percent_fbo": "Процент комиссии за продажу (FBO)",
    "sales_percent_fbs": "Процент комиссии за продажу (FBS)",
    "sales_percent": "Наибольший процент комиссии за продажу среди FBO и FBS",
}


def get_attrs_by_category_id(category_id: int) -> list:
    result = requests.post(
        "https://api-seller.ozon.ru/v3/category/attribute",
        headers=headers,
        data=json.dumps(
            {
                "category_id": [category_id],
            }
        ),
    ).json()["result"]
    return result


def write_headers_to_csv(file_path: str, fieldnames: list):
    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()


def calculate_product_dimensions(product: dict) -> dict:
    dimension_unit = product["dimension_unit"]
    prod_length = product["depth"]
    prod_width = product["width"]
    prod_height = product["height"]

    if dimension_unit == "mm":
        prod_length /= 100
        prod_width /= 100
        prod_height /= 100
    elif dimension_unit == "cm":
        prod_length /= 10
        prod_width /= 10
        prod_height /= 10
    elif dimension_unit == "in":
        prod_length = round(prod_length / 3.937, 1)
        prod_width = round(prod_width / 3.937, 1)
        prod_height = round(prod_height / 3.937, 1)

    return {"length": prod_length, "width": prod_width, "height": prod_height}


def calculate_product_weight_in_kg(product: dict) -> float:
    weight_unit = product["weight_unit"]
    prod_weight = product["weight"]

    if weight_unit == "g":
        prod_weight = round(prod_weight / 1000, 2)
    else:
        raise Exception("Неизвестная мера веса")

    return prod_weight


def get_product(limit=1000, last_id="") -> dict:
    result = requests.post(
        "https://api-seller.ozon.ru/v2/product/list",
        headers=headers,
        data=json.dumps(
            {
                "filter": {},
                "last_id": last_id,
                "limit": limit,
            }
        ),
    ).json()["result"]

    return result["items"], result["last_id"]


def get_product_id(products: list) -> list:
    return [item["product_id"] for item in products]


def get_product_info(product_id: int):
    result = requests.post(
        "https://api-seller.ozon.ru/v2/product/info",
        headers=headers,
        data=json.dumps({"product_id": product_id}),
    ).json()["result"]

    return result


def get_product_attributes(product_ids: list, limit=1000) -> list:
    response = requests.post(
        "https://api-seller.ozon.ru/v3/products/info/attributes",
        headers=headers,
        data=json.dumps(
            {
                "filter": {"product_id": [str(prod_id) for prod_id in product_ids]},
                "limit": limit,
            }
        ),
    )
    return response.json()["result"]


def get_price_objects(product_ids: list, limit=1000):
    result = requests.post(
        "https://api-seller.ozon.ru/v4/product/info/prices",
        headers=headers,
        data=json.dumps(
            {
                "filter": {
                    "product_id": [str(prod_id) for prod_id in product_ids],
                },
                "limit": limit,
            }
        ),
    ).json()["result"]["items"]
    return result


def get_product_price(product_ids: list, limit=1000):
    result = get_price_objects(product_ids, limit)
    product_price = {}
    for item in result:
        product_price[item["product_id"]] = item["price"]["price"]
    return product_price


def get_product_trading_schemes(product_ids: list, limit=1000) -> dict:
    result = requests.post(
        "https://api-seller.ozon.ru/v3/product/info/stocks",
        headers=headers,
        data=json.dumps(
            {
                "filter": {
                    "product_id": [str(prod_id) for prod_id in product_ids],
                },
                "limit": limit,
            }
        ),
    ).json()["result"]["items"]
    products_trading_schemes = {}
    for item in result:
        stocks = item["stocks"]
        trading_schemes = [
            stock["type"].upper()
            for stock in stocks
            if stock["present"] != 0 and stock["type"] in ["fbs", "fbo"]
        ]
        products_trading_schemes[item["product_id"]] = (
            trading_schemes if trading_schemes else [""]
        )

    return products_trading_schemes


def import_products_from_ozon_api_to_file(file_path: str):
    fieldnames = [
        "categories",
        "id_on_platform",
        "full_categories",
        "name",
        "description",
        "product_id",
        "length",
        "width",
        "height",
        "weight",
        "seller_name",
        "lower_threshold",
        "upper_threshold",
        "coefficient",
        "percent",
        "trading_scheme",
        "delivery_location",
        "price",
    ]
    write_headers_to_csv(file_path, fieldnames)
    limit = 1000
    last_id = ""
    products = ["" for _ in range(limit)]
    while len(products) == limit:
        products, last_id = get_product(limit=limit, last_id=last_id)
        prod_ids = get_product_id(products)
        products_attrs = get_product_attributes(prod_ids, limit=limit)
        products_trading_schemes = get_product_trading_schemes(prod_ids, limit=limit)
        products_prices = get_product_price(prod_ids, limit=limit)

        products_rows = []
        for prod in products_attrs:
            attrs = prod["attributes"]
            for a in attrs:
                if a["attribute_id"] == 9461:
                    category_name = a["values"][0]["value"]
                if a["attribute_id"] == 22387:
                    parent_category = a["values"][0]["value"]
                if a["attribute_id"] == 4191:
                    description = a["values"][0]["value"]

            id_on_platform = prod["id"]
            product_id = int(prod["offer_id"])
            name = prod["name"]
            dimensions = calculate_product_dimensions(prod)
            weight = calculate_product_weight_in_kg(prod)
            price = products_prices[id_on_platform]
            trading_schemes = products_trading_schemes[id_on_platform]
            for trad_scheme in trading_schemes:
                row = {
                    "categories": category_name,
                    "id_on_platform": id_on_platform,
                    "full_categories": parent_category,
                    "name": name,
                    "description": description,
                    "product_id": product_id,
                    "length": dimensions["length"],
                    "width": dimensions["width"],
                    "height": dimensions["height"],
                    "weight": weight,
                    "seller_name": "Продавец",
                    "lower_threshold": 0,
                    "upper_threshold": 0,
                    "coefficient": 0,
                    "percent": 0,
                    "trading_scheme": trad_scheme,
                    "delivery_location": "",
                    "price": price,
                }
                products_rows.append(row)

        with open(file_path, "a", newline="") as csvfile:
            for prod in products_rows:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow(prod)

    return


def get_product_commissions(product_ids: list, limit=1):
    result = get_price_objects(product_ids, limit)

    product_comissions = {}
    for item in result:
        product_comissions[item["product_id"]] = {
            "acquiring": item["acquiring"],
            **item["commissions"],
        }
    return product_comissions


def import_comissions_by_categories_from_ozon_api_to_file(file_path: str):
    fieldnames = [
        "commission_name",
        "category_name",
        "trading_scheme",
        "value",
        "commission_type",
        "delivery_location",
    ]
    write_headers_to_csv(file_path, fieldnames)
    limit = 1000
    last_id = ""
    products = ["" for _ in range(limit)]
    structure = {}

    while len(products) == limit:
        products, last_id = get_product(limit=limit, last_id=last_id)
        prod_ids = get_product_id(products)
        products_attrs = get_product_attributes(prod_ids, limit=limit)
        commissions_rows = []
        for prod in products_attrs:
            product_id = prod["id"]
            attrs = prod["attributes"]
            for a in attrs:
                if a["attribute_id"] == 9461:
                    category_name = a["values"][0]["value"]

            if structure.get(category_name):
                continue
            else:
                structure[category_name] = True

            prod_info = get_product_info(product_id)

            for com in prod_info["commissions"]:
                if com["sale_schema"] == "fbo":
                    com_name = "Процент комиссии за продажу (FBO)"
                    trad_scheme = "FBO"
                elif com["sale_schema"] == "fbs":
                    com_name = "Процент комиссии за продажу (FBS)"
                    trad_scheme = "FBS"
                elif com["sale_schema"] == "rfbs":
                    com_name = "Процент комиссии за продажу (rFBS)"
                    trad_scheme = "rFBS"
                percent = com["percent"]

                row = {
                    "category_name": category_name,
                    "commission_name": com_name,
                    "trading_scheme": trad_scheme,
                    "value": percent,
                    "commission_type": "percent",
                    "delivery_location": "",
                }
                commissions_rows.append(row)

        with open(file_path, "a", newline="") as csvfile:
            for row in commissions_rows:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow(row)

    return


def import_products_commission_from_ozon_api_to_file(file_path: str):
    fieldnames = ["id_on_platform", *list(COMMISSIONS.keys())]
    write_headers_to_csv(file_path, fieldnames)
    limit = 1000
    last_id = ""
    products = ["" for _ in range(limit)]

    while len(products) == limit:
        products, last_id = get_product(limit=limit, last_id=last_id)
        prod_ids = get_product_id(products)
        prod_commissions = get_product_commissions(prod_ids, limit=limit)
        commissions_rows = []
        for prod_id in prod_ids:
            commissions = prod_commissions[prod_id]
            row = {"id_on_platform": prod_id, **commissions}
            commissions_rows.append(row)

        with open(file_path, "a", newline="") as csvfile:
            for row in commissions_rows:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow(row)

    return
