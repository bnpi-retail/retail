from odoo import models, fields, api


class HistoryOfProductPositions(models.Model):
    _name = "ozon.history_of_product_positions"
    _description = "История позиций товаров"
    _order = "timestamp desc"

    timestamp = fields.Date(string="Дата", default=fields.Date.today)
    id_product = fields.Char(string="Product ID", readonly=True)
    search_query = fields.Many2one("ozon.tracked_search_queries", string="Поисковый запрос")
    number = fields.Char(string="Номер позиции карточки Ozon")

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            id = record.id
            result.append(
                (id, f"{record.timestamp}, {record.search_query.name}")
            )
        return result
