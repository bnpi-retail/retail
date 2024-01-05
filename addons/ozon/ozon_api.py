import json

import os
import requests

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
