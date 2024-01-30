# -*- coding: utf-8 -*-
# from odoo import http


# class ManagerProfile(http.Controller):
#     @http.route('/manager_profile/manager_profile', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/manager_profile/manager_profile/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('manager_profile.listing', {
#             'root': '/manager_profile/manager_profile',
#             'objects': http.request.env['manager_profile.manager_profile'].search([]),
#         })

#     @http.route('/manager_profile/manager_profile/objects/<model("manager_profile.manager_profile"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('manager_profile.object', {
#             'object': obj
#         })
