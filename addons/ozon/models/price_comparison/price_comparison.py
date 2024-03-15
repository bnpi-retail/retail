from collections import namedtuple
from datetime import datetime, time, timedelta
from itertools import chain

from odoo import models, fields, api

from .price_component import NAME_IDENTIFIER, BASE_CALCULATION_COMPONENTS, IDENTIFIER_NAME


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
        string="Факт - рынок", compute="_compute_diff_fact_market"
    )
    diff_plan_fact = fields.Float(
        string="План - факт", compute="_compute_diff_plan_fact"
    )
    calc_value = fields.Float(string="Калькулятор")

    comment = fields.Text(string="Комментарий")
    # String representations
    string_plan_value = fields.Char(string="План", compute="_compute_string")
    string_market_value = fields.Char(string="Рынок", compute="_compute_string")
    string_fact_value = fields.Char(string="Факт", compute="_compute_string")
    string_calc_value = fields.Char(string="Калькулятор", compute="_compute_string")

    # Compute methods
    def _compute_string(self):
        str_format = "%d.%m.%Y"
        for r in self:
            if r.name == "Дата расчёта":
                r.string_plan_value = datetime.fromtimestamp(r.plan_value).strftime(str_format)
                r.string_market_value = datetime.fromtimestamp(r.market_value).strftime(str_format)
                r.string_fact_value = datetime.fromtimestamp(r.fact_value).strftime(str_format)
                r.string_calc_value = datetime.fromtimestamp(r.calc_value).strftime(str_format)
            else:
                r.string_plan_value = str(round(r.plan_value, 2))
                r.string_market_value = str(round(r.market_value, 2))
                r.string_fact_value = str(round(r.fact_value, 2))
                r.string_calc_value = str(round(r.calc_value, 2))

    def _compute_diff_fact_market(self):
        for r in self:
            r.diff_fact_market = r.fact_value - r.market_value

    def _compute_diff_plan_fact(self):
        for r in self:
            r.diff_plan_fact = r.plan_value - r.fact_value

    def collect_product_data(self, product, **kwargs) -> list:
        """Collects all data needed to create price_comparison_ids for product."""
        p_id = product.id
        Row = namedtuple(
            "Row",
            [
                "group",
                "plan_value",
                "market_value",
                "fact_value",
                "calc_value",
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
        market_value = product.calculated_pricing_strategy_ids.filtered(
            lambda r: r.strategy_id == "lower_min_competitor"
        ).expected_price
        if not market_value:
            market_value = product.get_minimal_competitor_price()
        buyer_price = Row(
            group, plan_value=0, market_value=market_value, fact_value=product.marketing_price, calc_value=0, 
            price_component_id=pc.id
        )
        # Ваша цена
        pc = pcm.get("your_price")
        plan_price = self.env["ozon.base_calculation"].calculate_plan_price(product)
        market_value = buyer_price.market_value / (1 - product.category_marketing_discount)
        your_price = Row(
            group,
            plan_value=plan_price,
            market_value=market_value,
            fact_value=product.price,
            calc_value=kwargs.get('calc_price', 0),
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
        cost_price = Row(group, cp, cp, cp, cp, pc.id)
        data_ozon_expenses.append(cost_price)
        # Логистика - fix
        pc = pcm.get("logistics")
        plan_log = product.base_calculation_ids.filtered(
            lambda r: r.price_component_id == pc
        ).value
        fact_log = sum(product._logistics.mapped("value"))
        data_ozon_expenses.append(Row(group, plan_log, fact_log, fact_log, fact_log, pc.id))
        # Последняя миля - percent
        pc = pcm.get("last_mile")
        coef = (
            product.base_calculation_ids.filtered(
                lambda r: r.price_component_id == pc
            ).value
            / 100
        )
        plan_lm = your_price.plan_value * coef
        fact_percent = product._last_mile.percent
        market_lm = your_price.market_value * fact_percent
        fact_lm = product._last_mile.value
        calc_lm = your_price.calc_value * fact_percent
        data_ozon_expenses.append(Row(group, plan_lm, market_lm, fact_lm, calc_lm, pc.id))
        # Эквайринг - percent
        pc = pcm.get("acquiring")
        coef = (
            product.base_calculation_ids.filtered(
                lambda r: r.price_component_id == pc
            ).value
            / 100
        )
        plan_acq = your_price.plan_value * coef
        fact_percent = product._acquiring.percent
        market_acq = your_price.market_value * fact_percent
        fact_acq = product._acquiring.value
        calc_acq = your_price.calc_value * fact_percent
        data_ozon_expenses.append(Row(group, plan_acq, market_acq, fact_acq, calc_acq, pc.id))
        # Вознаграждение Ozon (комиссия Ozon) - percent
        pc = pcm.get("ozon_reward")
        coef = (
            product.base_calculation_ids.filtered(
                lambda r: r.price_component_id == pc
            ).value
            / 100
        )
        plan_reward = your_price.plan_value * coef
        total_ozon_reward_expenses = sum(product._ozon_reward.mapped("value"))
        fact_percent = total_ozon_reward_expenses / product.price
        market_reward = your_price.market_value * fact_percent
        fact_reward = total_ozon_reward_expenses
        calc_reward = your_price.calc_value * fact_percent
        data_ozon_expenses.append(
            Row(group, plan_reward, market_reward, fact_reward, calc_reward, pc.id)
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
        fact_percent = product._promo.percent
        market_promo = your_price.market_value * fact_percent
        fact_promo = product._promo.value
        calc_promo = your_price.calc_value * fact_percent
        data_ozon_expenses.append(
            Row(group, plan_promo, market_promo, fact_promo, calc_promo, pc.id)
        )
        # Обработка - fix
        pc = pcm.get("processing")
        proc = product.base_calculation_ids.filtered(
            lambda r: r.price_component_id == pc
        ).value
        fact_proc = sum(product._processing.mapped("value"))
        data_ozon_expenses.append(Row(group, proc, fact_proc, fact_proc, fact_proc, pc.id))
        # Обратная логистика
        pc = pcm.get("return_logistics")
        ret_log = product.base_calculation_ids.filtered(
            lambda r: r.price_component_id == pc
        ).value
        fact_ret_log = sum(product._return_logistics.mapped("value"))
        data_ozon_expenses.append(Row(group, ret_log, fact_ret_log, fact_ret_log, fact_ret_log, pc.id))

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
            data_company_expenses.append(Row(group, val, val, val, val, pc.id))

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
        fact_percent = product._tax.percent
        market_tax = your_price.market_value * fact_percent
        fact_tax = product._tax.value
        calc_tax = your_price.calc_value * fact_percent
        tax = Row(group, plan_tax, market_tax, fact_tax, calc_tax, pc.id)

        ### Показатели
        group = "Показатели"
        data_indicators = []
        # Сумма расходов
        pc = pcm.get("total_expenses")
        pv, mv, fv, cv = 0, 0, 0, 0
        for i in chain(data_ozon_expenses, data_company_expenses, [tax]):
            pv += i.plan_value
            mv += i.market_value
            fv += i.fact_value
            cv += i.calc_value
        total_expenses = Row(group, pv, mv, fv, cv, pc.id)
        data_indicators.append(total_expenses)
        # Прибыль
        pc = pcm.get("profit")
        profit = Row(
            group,
            plan_value=your_price.plan_value - total_expenses.plan_value,
            market_value=your_price.market_value - total_expenses.market_value,
            fact_value=your_price.fact_value - total_expenses.fact_value,
            calc_value=your_price.calc_value - total_expenses.calc_value,
            price_component_id=pc.id,
        )
        data_indicators.append(profit)
        # ROS (доходность, рентабельность продаж)
        pc = pcm.get("ros")
        ros = Row(
            group,
            plan_value=profit.plan_value / your_price.plan_value,
            market_value=your_price.market_value and profit.market_value / your_price.market_value,
            fact_value=your_price.fact_value and profit.fact_value / your_price.fact_value,
            calc_value=your_price.calc_value and profit.calc_value / your_price.calc_value,
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
            calc_value=your_price.calc_value - cost_price.calc_value,
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
            calc_value=margin.calc_value / cost_price.calc_value,
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
            calc_value=profit.calc_value / cost_price.calc_value,
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

    def update_for_products(self, products, **kwargs):
        products.price_comparison_ids.unlink()
        data = []
        for i, prod in enumerate(products):
            prod.update_current_product_all_expenses(prod.price)
            data.extend(self.collect_product_data(prod, **kwargs))
            print(f"{i} - price_comparison_ids were updated")
        self.create(data)

    
    def fill_with_blanks_if_not_exist(self, product):
        if len(product.price_comparison_ids) != len(IDENTIFIER_NAME):
            product.price_comparison_ids.unlink()
            pcm = self.env["ozon.price_component"]
            data = []
            for pc_identifier in IDENTIFIER_NAME:
                pc = pcm.get(pc_identifier)
                data.append({
                    "product_id": product.id,
                    "price_component_id": pc.id,
                })
            self.create(data)

    def update_plan_column_for_product(self, product):
        # Ваша цена
        your_price = product._price_comparison("your_price")
        your_price_plan_val = self.env["ozon.base_calculation"].calculate_plan_price(product)
        your_price.write({"plan_value": your_price_plan_val})
        # Цена для покупателя
        buyer_price = product._price_comparison("buyer_price")
        buyer_price.write({"plan_value": (your_price_plan_val 
                                          - your_price_plan_val * product.category_marketing_discount)})
        total_expenses_sum = 0
        # Fix
        for pc_identifier in ["cost", "logistics", "processing", "return_logistics", 
                              "company_processing_and_storage", "company_packaging", 
                              "company_marketing", "company_operators"]:
            price_comparison = product._price_comparison(pc_identifier)
            plan_value = product._base_calculation(pc_identifier).value
            price_comparison.write({"plan_value": plan_value})
            total_expenses_sum += plan_value
        # Percent
        for pc_identifier in ["last_mile", "acquiring", "ozon_reward", "promo", "tax"]:
            price_comparison = product._price_comparison(pc_identifier)
            percent = product._base_calculation(pc_identifier).value / 100
            plan_value = your_price.plan_value * percent
            price_comparison.write({"plan_value": plan_value})
            total_expenses_sum += plan_value
        ### Показатели
        self.write_price_comparison_indicators_for_column(product, "plan_value")

    def update_fact_column_for_product(self, product):
        # Цена для покупателя
        buyer_price = product._price_comparison("buyer_price")
        buyer_price.write({"fact_value": product.marketing_price})
        # Ваша цена
        your_price = product._price_comparison("your_price")
        your_price.write({"fact_value": product.price})
        self.write_price_comparison_expenses_for_column(product, "fact_value")
        self.write_price_comparison_indicators_for_column(product, "fact_value")
    
    def update_market_column_for_product(self, product):
        # Цена для покупателя
        buyer_price = product._price_comparison("buyer_price")
        market_value = product.calculated_pricing_strategy_ids.filtered(
            lambda r: r.strategy_id == "lower_min_competitor"
        ).expected_price
        if not market_value:
            market_value = product.get_minimal_competitor_price()
        buyer_price.write({"market_value": market_value})
        # Ваша цена
        your_price = product._price_comparison("your_price")
        yp = buyer_price.market_value / (1 - product.category_marketing_discount)
        your_price.write({"market_value": yp})
        self.write_price_comparison_expenses_for_column(product, "market_value")
        self.write_price_comparison_indicators_for_column(product, "market_value")
    
    def update_calc_column_for_product(self, product):
        your_price = product._price_comparison("your_price")
        your_price_calc_value = product.calc_column_your_price
        your_price.write({"calc_value": your_price_calc_value})
        buyer_price = product._price_comparison("buyer_price")
        buyer_price.write({"calc_value": (your_price_calc_value
                                          - your_price_calc_value * product.category_marketing_discount)})
        self.write_price_comparison_expenses_for_column(product, "calc_value")
        self.write_price_comparison_indicators_for_column(product, "calc_value")
    
    def get_column_expenses_sum(self, product, column):
        pc_identifiers = [i for i in BASE_CALCULATION_COMPONENTS if i != "roe"]
        return sum(product.price_comparison_ids.filtered(
            lambda r: r.price_component_id.identifier in pc_identifiers).mapped(column))

    def write_price_comparison_expenses_for_column(self, product, column):
        price = product._price_comparison("your_price")[column]
        ### Расходы Ozon
        # Себестоимость
        cost_price = product.retail_product_total_cost_price
        cost = product._price_comparison("cost")
        cost.write({column: cost_price})
        # Логистика
        logistics = product._price_comparison("logistics")
        logistics.write({column: sum(product._logistics.mapped("value"))})
        # Последняя миля
        last_mile = product._price_comparison("last_mile")
        percent = product._last_mile.percent
        last_mile.write({column: price * percent})
        # Эквайринг
        acquiring = product._price_comparison("acquiring")
        percent = product._acquiring.percent
        acquiring.write({column: price * percent})
        # Вознаграждение Ozon (комиссия Ozon)
        ozon_reward = product._price_comparison("ozon_reward")
        percent = sum(product._ozon_reward.mapped("percent"))
        ozon_reward.write({column: price * percent})
        # Реклама
        promo = product._price_comparison("promo")
        percent = product._promo.percent
        promo.write({column: price * percent})
        # Обработка
        processing = product._price_comparison("processing")
        processing.write({column: sum(product._processing.mapped("value"))})
        # Обратная логистика
        return_logistics = product._price_comparison("return_logistics")
        return_logistics.write({column: sum(product._return_logistics.mapped("value"))})
        ### Расходы компании
        for i in product.all_expenses_ids.filtered(lambda r: r.category == "Расходы компании"):
            pc_identifier = NAME_IDENTIFIER[i.name]
            price_comparison = product._price_comparison(pc_identifier)
            price_comparison.write({column: i.value})
        # Налог
        tax = product._price_comparison("tax")
        percent = product._tax.percent
        tax.write({column: price * percent})

    def write_price_comparison_indicators_for_column(self, product, column):
        price = product._price_comparison("your_price")[column]
        cost_price = product.retail_product_total_cost_price
        # Показатели
        # Сумма расходов
        total_expenses = product._price_comparison("total_expenses")
        total_expenses_sum = self.get_column_expenses_sum(product, column)
        total_expenses.write({column: total_expenses_sum})
        # Прибыль
        profit = product._price_comparison("profit")
        profit_val = price - total_expenses_sum
        profit.write({column: profit_val})
        # ROS (доходность, рентабельность продаж)
        ros = product._price_comparison("ros")
        ros.write({column: price and profit_val / price})
        # Наценка
        margin = product._price_comparison("margin")
        margin_val = price - cost_price
        margin.write({column: margin_val})
        # Процент наценки
        margin_percent = product._price_comparison("margin_percent")
        margin_percent.write({column: cost_price and margin_val / cost_price})
        # ROE (рентабельность инвестиций)
        roe = product._price_comparison("roe")
        roe.write({column: cost_price and profit_val / cost_price})
        # Дата расчёта
        calc_datetime = product._price_comparison("calc_datetime")
        calc_datetime.write({column: datetime.now().timestamp()})