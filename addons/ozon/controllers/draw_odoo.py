import json
import ast

from itertools import groupby
from operator import attrgetter
from datetime import datetime 

from odoo import http
from odoo.http import Response


class DrawOdooController(http.Controller):
    
    @http.route("/api/v1/get-data-for-draw-graphs", 
                auth="user", 
                csrf=False,
                methods=["GET"])
    def get_data_for_draw(self, **kwargs):
        model_sale = http.request.env["ozon.sale"]
        records = model_sale.search([("is_calculate", "=", True)])

        data = {}
        for record in records:
            if record.product not in data:
                data[record.product] = []
            data[record.product].append(record)
        
        data_for_graph = {}
        for product, records_list in data.items():
            if product not in data_for_graph:
                data_for_graph[product.id] = {"dates": [], "qty": [], "revenue": []}

            # Сортировка записей по дате
            records_list.sort(key=attrgetter('date'))

            # Группировка записей по дате
            grouped_records = {date.strftime("%Y-%m-%d"): list(group) for date, group in groupby(records_list, key=lambda x: x.date)}

            # Получение списка всех недель в течение года
            all_weeks = {datetime.strptime(f'2022-W{i}-1', "%Y-W%W-%w").strftime("%Y-%m-%d"): [] for i in range(1, 53)}

            # Заполнение данных для каждой недели
            for week, records in all_weeks.items():
                if week in grouped_records:
                    # Если есть записи для недели, добавляем их в данные
                    all_weeks[week] = [{"date": date, "qty": record.qty, "revenue": record.revenue} for date, group in grouped_records.items() for record in group]
                else:
                    # Если нет записей, добавляем нулевые значения
                    all_weeks[week] = [{"date": week, "qty": 0, "revenue": 0}]

            # Преобразование данных в список словарей для сериализации
            serialized_records = [record for week_records in all_weeks.values() for record in week_records]

            # Добавление группированных данных в data_for_graph
            data_for_graph[product.id] = serialized_records

        json_response = json.dumps(data_for_graph)
        return http.Response(json_response, content_type="application/json")

    @http.route("/api/v1/api/v1/save-images-for-lots", 
                auth="user", 
                type="http", 
                csrf=False, 
                methods=["POST"])
    def save_images(self, data, **post):
        data = ast.literal_eval(data)
        
        model_products = http.request.env["ozon.products"]
        model_stock = http.request.env["ozon.stock"]

        for sku, info in data.items():
            product = model_products \
                .search([("id_on_platform", "=", sku)], limit=1)
            
            model_stock.create({
                "product": product.id,
                "stocks_fbs": info["present"],
                "stocks_reserved_fbs": info["reserved"],
            })

        response_data = {"response": "success", "message": "Processed successfully"}
        response_json = json.dumps(response_data)
        status_code = 200

        return Response(
            response=response_json,
            status=status_code,
            content_type="application/json"
        )