from odoo import models, fields, api

class DraftProduct(models.Model):
    _name = "ozon.draft_product"
    _description = "Товар-черновик"

    name = fields.Char(string="Название")
    article = fields.Char(string="Артикул")
    cost_price = fields.Float(string="Себестоимость")
    category_id = fields.Many2one("ozon.categories", string="Категория Ozon")
    base_calculation_ids = fields.One2many ("ozon.base_calculation", "draft_product_id", 
                                            string="Плановый расчёт", 
        domain=[("price_component_id.identifier", "not in", ["calc_datetime", "buyer_price"])])
    base_calculation_template_id = fields.Many2one("ozon.base_calculation_template", 
                                                   string="Шаблон планового расчёта")
    products_competitors_ids = fields.Many2many("ozon.products_competitors", string="Товары-конкуренты" )
    mass_calculator_id = fields.Many2one("ozon.mass_calculator", string="Массовый калькулятор")

    @api.model
    def create(self, values):
        rec = super(DraftProduct, self).create(values)
        base_calculation_data = []
        for pc in self.env["ozon.price_component"].search([]):
            data = {}
            if pc.identifier == "ozon_reward":
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
    

    def _base_calculation(self, identifier):
        return self.base_calculation_ids.filtered(
            lambda r: r.price_component_id.identifier == identifier)
    
    
    def update_base_calculation_ids(self):
        price = self._base_calculation("your_price").value
        cost_price = self._base_calculation("cost").value
        if self.category_id:
            ozon_reward_value = self.category_id._trading_scheme_fees().get("Процент комиссии за продажу (FBS)", 0)
            ozon_reward = self._base_calculation("ozon_reward")
            ozon_reward.write({"value": ozon_reward_value})
        total_expenses_value = self.base_calculation_ids.calculate_total_expenses()
        total_expenses = self._base_calculation("total_expenses")
        total_expenses.write({"value": total_expenses_value})
        profit = self._base_calculation("profit")
        profit_value = price - total_expenses_value
        profit.write({"value": profit_value})
        ros = self._base_calculation("ros")
        ros.write({"value": price and (profit_value / price) * 100})
        margin = self._base_calculation("margin")
        margin_value = price - cost_price
        margin.write({"value": margin_value})
        margin_percent = self._base_calculation("margin_percent")
        margin_percent.write({"value": cost_price and margin_value / cost_price})
        roe = self._base_calculation("roe")
        roe.write({"value": cost_price and profit_value / cost_price})
        