from odoo import models, fields, api

class DraftProduct(models.Model):
    _name = "ozon.draft_product"
    _description = "Товар-черновик"

    name = fields.Char(string="Название")
    cost_price = fields.Float(string="Себестоимость")
    category_id = fields.Many2one("ozon.categories", string="Категория Ozon")
    base_calculation_ids = fields.One2many ("ozon.base_calculation", "draft_product_id", 
                                            string="Плановый расчёт", domain=[("price_component_id.identifier", "!=", "calc_datetime")])
    

    @api.model
    def create(self, values):
        rec = super(DraftProduct, self).create(values)
        base_calculation_data = []
        for pc in self.env["ozon.price_component"].search([]):
            data = {}
            if pc.identifier == "cost":
                data.update({"value": -values.get("cost_price", 0)})
            elif pc.identifier == "ozon_reward":
                if values.get("category_id"):
                    ozon_fees = rec.category_id._trading_scheme_fees()
                    data.update({
                        "value": ozon_fees.get("Процент комиссии за продажу (FBS)", 0),
                        "comment":(f"Комиссии категории:\n"
                                            f"{ozon_fees}"
                                            f"По умолчанию берётся комиссия категори по схеме FBS")})
            data.update({"draft_product_id": rec.id, "price_component_id": pc.id})

            base_calculation_data.append(data)

        self.env["ozon.base_calculation"].create(base_calculation_data)
        return rec