from odoo import models, fields, api

class DraftProduct(models.Model):
    _name = "ozon.draft_product"
    _description = "Товар-черновик"

    name = fields.Char(string="Название")
    article = fields.Char(string="Артикул")
    retail_product_total_cost_price = fields.Float(string="Себестоимость")
    category_id = fields.Many2one("ozon.categories", string="Категория Ozon")
    base_calculation_ids = fields.One2many ("ozon.base_calculation", "draft_product_id", 
                                            string="Плановый расчёт", 
        domain=[("price_component_id.identifier", "not in", ["calc_datetime", "buyer_price"])])
    base_calculation_template_id = fields.Many2one("ozon.base_calculation_template", 
                                                   string="Шаблон планового расчёта")
    products_competitors_ids = fields.Many2many("ozon.products_competitors", string="Товары-конкуренты")
    logistics_tariff_id = fields.Many2one("ozon.logistics_tariff", 
                                          string="Тариф логистики в плановом расчёте",
                                          default=lambda self: self._default_logistics_tariff_id())
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
    
    def _default_logistics_tariff_id(self):
        return self.env["ozon.logistics_tariff"].search(
            [("name", "=", "От 0,1 до 5 литров включительно — 76 рублей")]).id
        
class DraftProductPlanCalculation(models.Model):
    _inherit = "ozon.draft_product"

    plan_your_price = fields.Float(string="Ваша цена (План)", help="Ваша цена (План)")
    plan_logistics = fields.Float(string="Логистика (План)", help="Логистика (План)")
    plan_last_mile = fields.Float(string="Последняя миля (План)", help="Последняя миля (План)")
    plan_acquiring = fields.Float(string="Эквайринг (План)", help="Эквайринг (План)")
    plan_ozon_reward = fields.Float(string="Вознаграждение Ozon (План)", help="Вознаграждение Ozon (План)")
    plan_promo = fields.Float(string="Реклама (План)", help="Реклама (План)")
    plan_processing = fields.Float(string="Обработка (План)", help="Обработка (План)")
    plan_return_logistics = fields.Float(string="Обратная логистика (План)", help="Обратная логистика (План)")
    plan_tax = fields.Float(string="Налог (План)", help="Налог (План)")
    plan_total_expenses = fields.Float(string="Сумма расходов (План)", help="Сумма расходов (План)")
    plan_profit = fields.Float(string="Прибыль (План)", help="Прибыль (План)")
    plan_ros = fields.Float(string="ROS (План)", help="ROS (План)")
    plan_margin = fields.Float(string="Наценка (План)", help="Наценка (План)")
    plan_roe = fields.Float(string="ROE (План)", help="ROE (План)")

    def calculate_plan_items(self):
        pass

class DraftProductMarketCalculation(models.Model):
    _inherit = "ozon.draft_product"

    market_your_price = fields.Float(string="Ваша цена (Рынок)", help="Ваша цена (Рынок)")
    market_logistics = fields.Float(string="Логистика (Рынок)", help="Логистика (Рынок)")
    market_last_mile = fields.Float(string="Последняя миля (Рынок)", help="Последняя миля (Рынок)")
    market_acquiring = fields.Float(string="Эквайринг (Рынок)", help="Эквайринг (Рынок)")
    market_ozon_reward = fields.Float(string="Вознаграждение Ozon (Рынок)", help="Вознаграждение Ozon (Рынок)")
    market_promo = fields.Float(string="Реклама (Рынок)", help="Реклама (Рынок)")
    market_processing = fields.Float(string="Обработка (Рынок)", help="Обработка (Рынок)")
    market_return_logistics = fields.Float(string="Обратная логистика (Рынок)", help="Обратная логистика (Рынок)")
    market_tax = fields.Float(string="Налог (Рынок)", help="Налог (Рынок)")
    market_total_expenses = fields.Float(string="Сумма расходов (Рынок)", help="Сумма расходов (Рынок)")
    market_profit = fields.Float(string="Прибыль (Рынок)", help="Прибыль (Рынок)")
    market_ros = fields.Float(string="ROS (Рынок)", help="ROS (Рынок)")
    market_margin = fields.Float(string="Наценка (Рынок)", help="Наценка (Рынок)")
    market_roe = fields.Float(string="ROE (Рынок)", help="ROE (Рынок)")

