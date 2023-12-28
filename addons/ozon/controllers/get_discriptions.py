import json

from odoo import http


class LotsForGPTController(http.Controller):
    @http.route("/get-descriptions-lots", auth="user", csrf=False, methods=["GET"])
    def lots_for_gpt(self, **kwargs):
        model_ozon_lots_for_gpt = http.request.env["ozon.lots_for_gpt"]
        record = model_ozon_lots_for_gpt \
            .search([('status', '=', 'available')], limit=1)

        if record:
            record.write({'status': 'in_processing'})
            payload = {
                'message': True, 
                'id': record.id, 
                'desscription': record.product.description
            }
        else:
            payload = {'message': False}

        json_response = json.dumps(payload)
        return http.Response(json_response, content_type='application/json')

    @http.route("/set-searches-queries", auth="user", csrf=False, methods=["POST"])
    def get_searches_queries(self, **post):
        request_data = http.request.httprequest.get_data(as_text=True)
        try:
            json_data = json.loads(request_data)
        except json.JSONDecodeError as e:
            error_response = {'error': 'Invalid JSON format'}
            json_error_response = json.dumps(error_response)
            return http.Response(json_error_response, content_type='application/json', status=400)
        
        id_param = json_data['id']
        message_param = json_data['message']
        
        record = http.request.env["ozon.lots_for_gpt"] \
            .search([('id', '=', id_param)], limit=1)
        
        model_tracked_search_queries = http.request.env["ozon.tracked_search_queries"]
        ids = []
        for answer in message_param:
            record_answer = model_tracked_search_queries.create({
                'name': answer
            })
            ids.append(record_answer.id)
        

        if record:
            record.product.write({'tracked_search_queries': [(6, 0, ids)]})
            record.write({'status': 'complete'})

        payload = {'message': True}
        json_response = json.dumps(payload)
        return http.Response(json_response, content_type='application/json')

