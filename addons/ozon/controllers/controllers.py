# -*- coding: utf-8 -*-
# from odoo import http


# class Ozon(http.Controller):
#     @http.route('/ozon/ozon', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ozon/ozon/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ozon.listing', {
#             'root': '/ozon/ozon',
#             'objects': http.request.env['ozon.ozon'].search([]),
#         })

#     @http.route('/ozon/ozon/objects/<model("ozon.ozon"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ozon.object', {
#             'object': obj
#         })
