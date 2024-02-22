from collections import namedtuple
from datetime import datetime, time, timedelta

from odoo import models, fields, api


class PriceComparison(models.Model):
    _name = "ozon.price_comparison"
    _description = "Сравнение цен"

    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    price_component_id = fields.Many2one(
        "ozon.price_component", string="Компонент цены"
    )

    name = fields.Char(
        string="Показатель (статья расходов, индикатор)",
        related="price_component_id.name",
    )
    group = fields.Char(string="Группа")
    plan_value = fields.Float(string="План")
    market_value = fields.Float(string="Рынок")
    fact_value = fields.Float(string="Факт")

    diff_fact_market = fields.Float(
        string="Отклонение (факт-рынок)", compute="_compute_diff_fact_market"
    )
    diff_plan_fact = fields.Float(
        string="Отклонение (план-факт)", compute="_compute_diff_plan_fact"
    )
    calc_value = fields.Float(string="Калькулятор")

    comment = fields.Text(string="Комментарий")

    # Compute methods
    def _compute_diff_fact_market(self):
        for r in self:
            r.diff_fact_market = r.fact_value - r.market_value

    def _compute_diff_plan_fact(self):
        for r in self:
            r.diff_plan_fact = r.plan_value - r.fact_value

    def collect_product_data(self, product) -> list:
        """Collects all data needed to create price_comparison_ids for product."""
        p_id = product.id
        Row = namedtuple(
            "Row",
            [
                "group",
                "plan_value",
                "market_value",
                "fact_value",
                "price_component_id",
                "product_id",
            ],
            defaults=[p_id],
        )
        pcm = self.env["ozon.price_component"]
        ### Цены
        group = "Цены"
        # Цена для покупателя TODO: откуда брать?
        pc = pcm.get("buyer_price")
        buyer_price = Row(
            group, plan_value=0, market_value=0, fact_value=0, price_component_id=pc.id
        )
        # Ваша цена
        pc = pcm.get("your_price")
        plan_price = self.env["ozon.base_calculation"].calculate_plan_price(product)
        market_price = product.calculated_pricing_strategy_ids.filtered(
            lambda r: r.strategy_id == "lower_min_competitor"
        ).expected_price
        if not market_price:
            market_price = product.get_minimal_competitor_price()
        your_price = Row(
            group,
            plan_value=plan_price,
            market_value=market_price,
            fact_value=product.price,
            price_component_id=pc.id,
        )
        data_prices = [buyer_price, your_price]

        ### Расходы Ozon
        data_ozon_expenses = []
        group = "Расходы Ozon"
        # Себестоимость - fix
        pc = pcm.get("cost")
        cp = product.fix_expenses.filtered(
            lambda r: r.name == "Себестоимость товара"
        ).price
        if cp == 0:
            return [{"product_id": p_id, "comment": "Не задана себестоимость."}]
        cost_price = Row(group, cp, cp, cp, pc.id)
        data_ozon_expenses.append(cost_price)
        # Логистика - fix
        pc = pcm.get("logistics")
        plan_log = product.base_calculation_ids.filtered(
            lambda r: r.price_component_id == pc
        ).value
        fact_log = product._logistics.value
        data_ozon_expenses.append(Row(group, plan_log, plan_log, fact_log, pc.id))
        # Последняя миля - percent
        pc = pcm.get("last_mile")
        coef = (
            product.base_calculation_ids.filtered(
                lambda r: r.price_component_id == pc
            ).value
            / 100
        )
        plan_lm = your_price.plan_value * coef
        market_lm = your_price.market_value * coef
        fact_lm = product._last_mile.value
        data_ozon_expenses.append(Row(group, plan_lm, market_lm, fact_lm, pc.id))
        # Эквайринг - percent
        pc = pcm.get("acquiring")
        coef = (
            product.base_calculation_ids.filtered(
                lambda r: r.price_component_id == pc
            ).value
            / 100
        )
        plan_acq = your_price.plan_value * coef
        market_acq = your_price.market_value * coef
        fact_acq = product._acquiring.value
        data_ozon_expenses.append(Row(group, plan_acq, market_acq, fact_acq, pc.id))
        # Вознаграждение Ozon (комиссия Ozon) - percent
        pc = pcm.get("ozon_reward")
        coef = (
            product.base_calculation_ids.filtered(
                lambda r: r.price_component_id == pc
            ).value
            / 100
        )
        plan_reward = your_price.plan_value * coef
        market_reward = your_price.market_value * coef
        fact_reward = product._ozon_reward.value
        data_ozon_expenses.append(
            Row(group, plan_reward, market_reward, fact_reward, pc.id)
        )
        # Реклама - percent
        pc = pcm.get("promo")
        coef = (
            product.base_calculation_ids.filtered(
                lambda r: r.price_component_id == pc
            ).value
            / 100
        )
        plan_promo = your_price.plan_value * coef
        market_promo = your_price.market_value * coef
        fact_promo = product._promo.value
        data_ozon_expenses.append(
            Row(group, plan_promo, market_promo, fact_promo, pc.id)
        )
        # Обработка - fix
        pc = pcm.get("processing")
        proc = product.base_calculation_ids.filtered(
            lambda r: r.price_component_id == pc
        ).value
        fact_proc = product._processing.value
        data_ozon_expenses.append(Row(group, proc, proc, fact_proc, pc.id))
        # Обратная логистика - fix  TODO: depends on sales qty and returns
        pc = pcm.get("return_logistics")
        ret_log = product.base_calculation_ids.filtered(
            lambda r: r.price_component_id == pc
        ).value
        # TODO: как считать факт. обратную логистику?
        sales = product._last_30_days_sales
        returns = product._last_30_days_returns
        if len(product._last_30_days_sales) - len(returns) == 0:
            fact_ret_log = 0
        else:
            fact_ret_log = ((fact_log + fact_proc) * len(returns)) / (len(sales) - len(returns))
        data_ozon_expenses.append(Row(group, ret_log, ret_log, fact_ret_log, pc.id))

        ### Расходы компании
        # TODO: откуда брать расходы компании для стобца ФАКТ?
        group = "Расходы компании"
        data_company_expenses = []
        for i in [
            "company_processing_and_storage",
            "company_packaging",
            "company_marketing",
            "company_operators",
        ]:
            pc = pcm.get(i)
            val = product.base_calculation_ids.filtered(
                lambda r: r.price_component_id == pc
            ).value
            data_company_expenses.append(Row(group, val, val, val, pc.id))

        ### Налог
        # Налог - percent
        group = "Налог"
        pc = pcm.get("tax")
        coef = (
            product.base_calculation_ids.filtered(
                lambda r: r.price_component_id == pc
            ).value
            / 100
        )
        plan_tax = your_price.plan_value * coef
        market_tax = your_price.market_value * coef
        fact_tax = product._tax.value
        tax = Row(group, plan_tax, market_tax, fact_tax, pc.id)

        ### Показатели
        group = "Показатели"
        data_indicators = []
        # Сумма расходов
        pc = pcm.get("total_expenses")
        pv, mv, fv = 0, 0, 0
        for i in data_ozon_expenses + data_company_expenses:
            pv += i.plan_value
            mv += i.market_value
            fv += i.fact_value
        total_expenses = Row(group, pv, mv, fv, pc.id)
        data_indicators.append(total_expenses)
        # Прибыль
        pc = pcm.get("profit")
        profit = Row(
            group,
            plan_value=your_price.plan_value - total_expenses.plan_value,
            market_value=your_price.market_value - total_expenses.market_value,
            fact_value=your_price.fact_value - total_expenses.fact_value,
            price_component_id=pc.id,
        )
        data_indicators.append(profit)
        # ROS (доходность, рентабельность продаж)
        pc = pcm.get("ros")
        ros = Row(
            group,
            plan_value=profit.plan_value / your_price.plan_value,
            market_value=your_price.market_value
            and profit.market_value / your_price.market_value,
            fact_value=your_price.fact_value
            and profit.fact_value / your_price.fact_value,
            price_component_id=pc.id,
        )
        data_indicators.append(ros)
        # Наценка
        pc = pcm.get("margin")
        margin = Row(
            group,
            plan_value=your_price.plan_value - cost_price.plan_value,
            market_value=your_price.market_value - cost_price.market_value,
            fact_value=your_price.fact_value - cost_price.fact_value,
            price_component_id=pc.id,
        )
        data_indicators.append(margin)
        # Процент наценки
        pc = pcm.get("margin_percent")
        margin_percent = Row(
            group,
            plan_value=margin.plan_value / cost_price.plan_value,
            market_value=margin.market_value / cost_price.market_value,
            fact_value=margin.fact_value / cost_price.fact_value,
            price_component_id=pc.id,
        )
        data_indicators.append(margin_percent)
        # ROE (рентабельность инвестиций)
        pc = pcm.get("roe")
        roe = Row(
            group,
            plan_value=profit.plan_value / cost_price.plan_value,
            market_value=profit.market_value / cost_price.market_value,
            fact_value=profit.fact_value / cost_price.fact_value,
            price_component_id=pc.id,
        )
        data_indicators.append(roe)

        data = [
            i._asdict()
            for i in data_prices
            + data_ozon_expenses
            + data_company_expenses
            + [tax]
            + data_indicators
        ]
        return data

    def update_for_products(self, products):
        products.price_comparison_ids.unlink()
        data = []
        for i, prod in enumerate(products):
            data.extend(self.collect_product_data(prod))
            print(f"{i} - price_comparison_ids were updated")
        self.create(data)
