# -*- coding: utf-8 -*-
# from odoo import http


# class Retail(http.Controller):
#     @http.route('/retail/retail', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/retail/retail/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('retail.listing', {
#             'root': '/retail/retail',
#             'objects': http.request.env['retail.retail'].search([]),
#         })

#     @http.route('/retail/retail/objects/<model("retail.retail"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('retail.object', {
#             'object': obj
#         })
