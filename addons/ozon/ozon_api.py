import io
import json
import os
import re
import csv
import requests
import logging

from typing import Optional

logger = logging.getLogger(__name__)

OZON_CLIENT_ID = os.getenv("OZON_CLIENT_ID")
OZON_API_KEY = os.getenv("OZON_API_KEY")

if not OZON_CLIENT_ID or not OZON_API_KEY:
    raise ValueError("Env variables $OZON_CLIENT_ID and $OZON_API_KEY weren't found")

headers = {
    "Client-Id": OZON_CLIENT_ID,
    "Api-Key": OZON_API_KEY,
}

ALL_COMMISSIONS = {
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

FBO_FIX_COMMISSIONS = {
    "acquiring": "Максимальная комиссия за эквайринг",
    "fbo_fulfillment_amount": "Комиссия за сборку заказа (FBO)",
    "fbo_direct_flow_trans_min_amount": "Магистраль от (FBO)",
    "fbo_direct_flow_trans_max_amount": "Магистраль до (FBO)",
    "fbo_deliv_to_customer_amount": "Последняя миля (FBO)",
    "fbo_return_flow_amount": "Комиссия за возврат и отмену (FBO)",
    "fbo_return_flow_trans_min_amount": "Комиссия за обратную логистику от (FBO)",
    "fbo_return_flow_trans_max_amount": "Комиссия за обратную логистику до (FBO)",
}
FBO_PERCENT_COMMISSIONS = {
    "sales_percent_fbo": "Процент комиссии за продажу (FBO)",
}
FBS_FIX_COMMISSIONS = {
    "acquiring": "Максимальная комиссия за эквайринг",
    "fbs_first_mile_min_amount": "Минимальная комиссия за обработку отправления (FBS) — 0 рублей",
    "fbs_first_mile_max_amount": "Максимальная комиссия за обработку отправления (FBS) — 25 рублей",
    "fbs_direct_flow_trans_min_amount": "Магистраль от (FBS)",
    "fbs_direct_flow_trans_max_amount": "Магистраль до (FBS)",
    "fbs_deliv_to_customer_amount": "Последняя миля (FBS)",
    "fbs_return_flow_amount": "Комиссия за возврат и отмену, обработка отправления (FBS)",
    "fbs_return_flow_trans_min_amount": "Комиссия за возврат и отмену, магистраль от (FBS)",
    "fbs_return_flow_trans_max_amount": "Комиссия за возврат и отмену, магистраль до (FBS)",
}
FBS_PERCENT_COMMISSIONS = {
    "sales_percent_fbs": "Процент комиссии за продажу (FBS)",
}

MIN_FIX_EXPENSES_FBS = [
    "Себестоимость товара",
    "Максимальная комиссия за эквайринг",
    "Минимальная комиссия за обработку отправления (FBS) — 0 рублей",
    "Магистраль от (FBS)",
    "Последняя миля (FBS)",
    # "Комиссия за возврат и отмену, обработка отправления (FBS)",
    # "Комиссия за возврат и отмену, магистраль от (FBS)",
]
MAX_FIX_EXPENSES_FBS = [
    "Себестоимость товара",
    "Максимальная комиссия за эквайринг",
    "Максимальная комиссия за обработку отправления (FBS) — 25 рублей",
    "Магистраль до (FBS)",
    "Последняя миля (FBS)",
    # "Комиссия за возврат и отмену, обработка отправления (FBS)",
    # "Комиссия за возврат и отмену, магистраль до (FBS)",
]
MIN_FIX_EXPENSES_FBO = [
    "Себестоимость товара",
    "Максимальная комиссия за эквайринг",
    "Комиссия за сборку заказа (FBO)",
    "Магистраль от (FBO)",
    "Последняя миля (FBO)",
    # "Комиссия за возврат и отмену (FBO)",
    # "Комиссия за обратную логистику от (FBO)",
]
MAX_FIX_EXPENSES_FBO = [
    "Себестоимость товара",
    "Максимальная комиссия за эквайринг",
    "Комиссия за сборку заказа (FBO)",
    "Магистраль до (FBO)",
    "Последняя миля (FBO)",
    # "Комиссия за возврат и отмену (FBO)",
    # "Комиссия за обратную логистику до (FBO)",
]
MAX_FIX_EXPENSES = [
    "Себестоимость товара",
    "Максимальная комиссия за эквайринг",
    "Максимальная комиссия за обработку отправления (FBS) — 25 рублей",
    "Магистраль до (FBS)",
    "Последняя миля (FBS)",
    "Комиссия за возврат и отмену, обработка отправления (FBS)",
    "Комиссия за возврат и отмену, магистраль до (FBS)",
    "Комиссия за сборку заказа (FBO)",
    "Магистраль до (FBO)",
    "Последняя миля (FBO)",
    "Комиссия за возврат и отмену (FBO)",
    "Комиссия за обратную логистику до (FBO)",
]


def set_price(prices: list):
    """Takes as argument a list of prices = [
        {
            'product_id': int,
            'price': int,
        }
    ]
    """
    response = requests.post(
        "https://api-seller.ozon.ru/v1/product/import/prices",
        headers=headers,
        data=json.dumps({"prices": prices}),
    ).json()
    if response.get("result"):
        return response["result"]
    else:
        return response


def get_product_info_list_by_sku(sku_list: list):
    result = requests.post(
        "https://api-seller.ozon.ru/v2/product/info/list",
        headers=headers,
        data=json.dumps({"sku": sku_list}),
    ).json()

    return result["result"]["items"]


def get_product_id_by_sku(sku_list: list) -> list:
    product_info_list = get_product_info_list_by_sku(sku_list)
    product_ids = [i["id"] for i in product_info_list]
    return product_ids


def add_products_to_action(action_id, prod_list: list):
    """prod_list:
    [
        {
            "action_price": int,
            "product_id": int
        },
        ...
    ]
    """
    response = requests.post(
        "https://api-seller.ozon.ru/v1/actions/products/activate",
        headers=headers,
        data=json.dumps({"action_id": action_id, "products": prod_list}),
    ).json()

    return response["result"]


def delete_products_from_action(action_id, product_ids: list):
    response = requests.post(
        "https://api-seller.ozon.ru/v1/actions/products/deactivate",
        headers=headers,
        data=json.dumps({"action_id": action_id, "product_ids": product_ids}),
    ).json()

    return response["result"]


def postings_fbs_get(posting_number: str) -> dict:
    response = requests.post(
        "https://api-seller.ozon.ru/v3/posting/fbs/get",
        headers=headers,
        data=json.dumps({
            "posting_number": posting_number,
            "with": {
                "analytics_data": True,
                "barcodes": True,
                "financial_data": True,
                "product_exemplars": True,
                "translit": True
            }
        }),
    ).json()

    return response


def postings_fbo_get(posting_number: str) -> dict:
    response = requests.post(
        "https://api-seller.ozon.ru/v2/posting/fbo/get",
        headers=headers,
        data=json.dumps({
            "posting_number": posting_number,
            "with": {
                "analytics_data": True,
                "barcodes": True,
                "financial_data": True,
                "product_exemplars": True,
                "translit": True
            }
        }),
    ).json()

    return response


def get_posting_data(posting_number):
    res = None
    pattern = r"-\d{1,2}$"
    is_posting_number = True if re.search(pattern, posting_number) else False
    if is_posting_number:
        result = postings_fbs_get(posting_number)
        if result.get('result'):
            res = result.get('result')
        if not res:
            result = postings_fbo_get(posting_number)
            if result.get('result'):
                res = result.get('result')
    else:
        count = 1
        while count <= 10:
            probably_posting_number = posting_number + f'-{count}'
            result = postings_fbs_get(probably_posting_number)
            if result.get('result'):
                res = result.get('result')
                break
            result = postings_fbo_get(probably_posting_number)
            if result.get('result'):
                res = result.get('result')
                break
            count += 1

    return res


def get_posting_from_ozon_api(posting_number: str):
    fieldnames = [
        "in_process_at",
        "trading_scheme",
        "posting_number",
        "order_id",
        "order_number",
        "status",
        "region",
        "city",
        "warehouse_id",
        "warehouse_name",
        "cluster_from",
        "cluster_to",
        "products",
    ]
    posting_data = None
    result = get_posting_data(posting_number)

    if result:
        posting = result
        in_process_at = posting["in_process_at"]
        trading_scheme = "FBS" if posting.get("delivery_method") else "FBO"
        posting_number = posting["posting_number"]
        order_id = posting["order_id"]
        order_number = posting["order_number"]
        status = posting["status"]
        products = [{
            "offer_id": product["offer_id"],
            "price": product["price"],
            "quantity": product["quantity"],
            "sku": product["sku"],
        } for product in posting["products"]]

        if analytics_data := posting.get("analytics_data"):
            region = analytics_data["region"]
            city = analytics_data["city"]
            warehouse_id = analytics_data["warehouse_id"]
            if trading_scheme == "FBS":
                warehouse_name = posting["analytics_data"]["warehouse"]
            else:
                warehouse_name = posting["analytics_data"]["warehouse_name"]
        else:
            region, city, warehouse_id, warehouse_name = "", "", "", ""

        cluster_from = posting["financial_data"]["cluster_from"]
        cluster_to = posting["financial_data"]["cluster_to"]
        posting_data = {
            "in_process_at": in_process_at,
            "trading_scheme": trading_scheme,
            "posting_number": posting_number,
            "order_id": order_id,
            "order_number": order_number,
            "status": status,
            "region": region,
            "city": city,
            "warehouse_id": warehouse_id,
            "warehouse_name": warehouse_name,
            "cluster_from": cluster_from,
            "cluster_to": cluster_to,
            "products": products,
        }
        virtual_file = io.StringIO()
        writer = csv.DictWriter(virtual_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(posting_data)
        virtual_file.seek(0)
        posting_data = virtual_file.getvalue()
        virtual_file.close()

    return posting_data
