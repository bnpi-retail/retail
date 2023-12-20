from odoo import http


class OzonComputeCoefsAndGroups(http.Controller):
    @http.route(
        "/compute/products_coefs_and_groups",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def compute_ozon_products_coefs_and_groups(self):
        http.request.env["ozon.products"].update_coefs_and_groups()
        return "All products' coefs and groups were successfully computed."