from odoo import models, fields, api


class PriceComparison(models.Model):
    _name = "ozon.price_comparison"
    _description = "Сравнение цен"
    
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")

    name = fields.Char(string="Показатель (статья расходов, индикатор)")
    plan_value = fields.Float(string="План (базовый расчет)")
    market_value = fields.Float(string="Рынок")
    fact_value = fields.Float(string="Факт")

    diff_fact_market = fields.Float(string="Отклонение (факт-рынок)", 
                                     compute="_compute_diff_fact_market")
    diff_plan_fact = fields.Float(string="Отклонение (план-факт)",
                                    compute="_compute_diff_plan_fact")
    calc_value = fields.Float(string="Калькулятор")

    

    # Compute methods
    def _compute_diff_fact_market(self):
        for r in self:
            r.diff_fact_market = r.fact_value - r.market_value
    
    def _compute_diff_plan_fact(self):
        for r in self:
            r.diff_plan_fact = r.plan_value - r.fact_value