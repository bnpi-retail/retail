from odoo import http
import base64
import logging

logger = logging.getLogger(__name__)


class ImportImagesSale(http.Controller):
    @http.route(
        "/api/v1/draw_graphs_categories_products",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def run_draw_graphs(self, **kwargs):
        # categories = http.request.env["ozon.categories"].search([])
        categories = http.request.env["ozon.categories"].search([("name_categories", '=', 'Аккумулятор для ноутбука')])
        count = 0
        for cat in categories:
            logger.info(f"run_draw_graphs: {cat.name_categories} + category products")
            cat.action_draw_graphs_by_categories()
            count += 1

        logger.info(f"run_draw_graphs complete: all- {len(categories)}, done- {count}")

        return "Graphs drawing processed successfully."

    @http.route(
        "/api/v1/draw_graphs_competitors_products",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def run_draw_graphs_competitors_products(self, **kwargs):
        products_competitors = http.request.env["ozon.products_competitors"].search([])
        for prod in products_competitors:
            prod.draw_plot()

        return "Graphs drawing processed successfully."
