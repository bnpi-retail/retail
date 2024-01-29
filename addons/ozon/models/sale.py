from odoo import models, fields, api


class ProductSale(models.Model):
    _name = "ozon.sale"
    _description = "Продажи товаров"

    product = fields.Many2one("ozon.products", string="Товар Ozon")
    product_id_on_platform = fields.Char(
        string="Product ID",
        readonly=True,
        compute="_compute_product_id_on_platform",
        store=True,
    )
    date = fields.Date(string="Дата продажи", readonly=True)
    qty = fields.Integer(string="Кол-во проданного товара", readonly=True)
    revenue = fields.Float(string="Выручка", readonly=True)
    is_calculate = fields.Boolean(string="Учавствует в расчетах", default=False)
    total_qty = fields.Integer(
        string="Кол-во проданного товара за всё время", computed="_compute_total_qty"
    )
    total_revenue = fields.Float(
        string="Выручка по товару за всё время", computed="_compute_total_revenue"
    )

    @api.model
    def create(self, values):
        records = self.search([("product", "=", values.get("product"))])

        values["total_qty"] = 0
        values["total_revenue"] = 0
        for rec in records:
            values["total_qty"] += rec.qty
            values["total_revenue"] += rec.revenue

        return super(ProductSale, self).create(values)

    def _compute_product_id_on_platform(self):
        for rec in self:
            rec.product_id_on_platform = rec.product.id_on_platform
