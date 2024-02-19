from collections import namedtuple

from odoo import models, fields, api


class PriceComparison(models.Model):
    _name = "ozon.price_comparison"
    _description = "Сравнение цен"
    
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")

    name = fields.Char(string="Показатель (статья расходов, индикатор)")
    group = fields.Char(string="Группа")
    plan_value = fields.Float(string="План (базовый расчет)")
    market_value = fields.Float(string="Рынок")
    fact_value = fields.Float(string="Факт")

    diff_fact_market = fields.Float(string="Отклонение (факт-рынок)", 
                                     compute="_compute_diff_fact_market")
    diff_plan_fact = fields.Float(string="Отклонение (план-факт)",
                                    compute="_compute_diff_plan_fact")
    calc_value = fields.Float(string="Калькулятор")

    comment = fields.Text(string="Комментарий")

    # Compute methods
    def _compute_diff_fact_market(self):
        for r in self:
            r.diff_fact_market = r.fact_value - r.market_value
    
    def _compute_diff_plan_fact(self):
        for r in self:
            r.diff_plan_fact = r.plan_value - r.fact_value
    
    # Methods
    def create_row_based_on_price_row(self, RowClass, price_row, group, name, coef, max_val=0):
        if max_val == 0:
            plan_value = price_row.plan_value * coef
            market_value = price_row.market_value * coef
        else:
            plan_value = min(price_row.plan_value * coef, max_val)
            market_value = min(price_row.market_value * coef, max_val)
        row = RowClass(group=group, name=name,
                plan_value=plan_value,
                market_value=market_value,
                fact_value=0)
        return row
    
    def collect_product_data(self, product) -> list:
        """Collects all data needed to create price_comparison_ids for product."""
        p_id = product.id
        Row = namedtuple(
            "Row", 
            ["group", "name", "plan_value", "market_value", "fact_value", "product_id"], 
            defaults=[p_id])
        
        ### Цены
        group = "Цены"
        # TODO: Цена для покупателя - откуда брать?
        buyer_price = Row(group, name="Цена для покупателя", plan_value=0, market_value=0, fact_value=0)
        # TODO: Ваша цена. Откуда брать значения ПЛАН, рынок, ФАКТ?
        min_comp_price = product.get_minimal_competitor_price()
        fact_price = 0 # TODO
        your_price = Row(group, name="Ваша цена", plan_value=product.price, 
                         market_value=min_comp_price, fact_value=fact_price)
        data_prices = [buyer_price, your_price]

        ### Расходы Ozon
        data_ozon_expenses = []
        group = "Расходы Ozon"
        # Себестоимость - fix
        cp = product.retail_product_total_cost_price
        cost_price = Row(group, "Себестоимость", cp, cp, cp)
        if cp == 0:
            return [{"product_id": p_id, "comment": "Не задана себестоимость."}]
        data_ozon_expenses.append(cost_price)
        # Логистика - fix
        name = "Логистика"
        log = product.all_expenses_ids.filtered(lambda r: r.category == name).value
        data_ozon_expenses.append(Row(group, name, log, log, log))
        # Последняя миля - percent
        name = "Последняя миля"
        lm = product.all_expenses_ids.filtered(lambda r: r.category == name).percent
        last_mile = self.create_row_based_on_price_row(Row, your_price, group, name, lm, max_val=500)
        data_ozon_expenses.append(last_mile)
        # Эквайринг - percent
        name = "Эквайринг"
        acq = product.all_expenses_ids.filtered(lambda r: r.category == name).percent
        acquiring = self.create_row_based_on_price_row(Row, your_price, group, name, acq)
        data_ozon_expenses.append(acquiring)
        # Вознаграждение Ozon (комиссия Ozon) - percent
        name = "Вознаграждение Ozon"
        com = product.all_expenses_ids.filtered(lambda r: r.category == name).percent
        commission = self.create_row_based_on_price_row(Row, your_price, group, name, com)
        data_ozon_expenses.append(commission)
        # Реклама - percent
        name = "Средняя стоимость продвижения товара"
        promo_percent = product.all_expenses_ids.filtered(lambda r: r.name == name).percent
        promo = self.create_row_based_on_price_row(Row, your_price, group, name, promo_percent)
        data_ozon_expenses.append(promo)
        # Обработка - fix
        name = "Обработка"
        proc = product.all_expenses_ids.filtered(lambda r: r.category == name).value
        data_ozon_expenses.append(Row(group, name, proc, proc, proc))
        # Обратная логистика - fix  TODO: depends on sales qty and returns
        name = "Обратная логистика"
        data_ozon_expenses.append(Row(group, name, 0, 0, 0))

        ### Расходы компании
        group = "Расходы компании"
        data_company_expenses = []
        # TODO переделать - брать значения из модели Конструктор цен
        name = "Обработка и хранение"
        data_company_expenses.append(Row(group, name, 0, 0, 0))
        name = "Упаковка"
        data_company_expenses.append(Row(group, name, 0, 0, 0))
        name = "Маркетинг"
        data_company_expenses.append(Row(group, name, 0, 0, 0))
        name = "Операторы"
        data_company_expenses.append(Row(group, name, 0, 0, 0))

        ### Налог
        # Налог - percent
        name, group = "Налог", "Налог"
        t_percent = product.all_expenses_ids.filtered(lambda r: r.name == name).percent
        tax = self.create_row_based_on_price_row(Row, your_price, group, name, t_percent)

        ### Показатели
        group = "Показатели"
        data_indicators = []
        # Сумма расходов
        pv, mv, fv = 0, 0, 0
        for i in data_ozon_expenses + data_company_expenses:
            pv += i.plan_value
            mv += i.market_value
            fv += i.fact_value
        total_expenses = Row(group, "Сумма расходов", pv, mv, fv)
        data_indicators.append(total_expenses)
        # Прибыль
        profit = Row(group, "Прибыль", 
                     plan_value=your_price.plan_value - total_expenses.plan_value,
                     market_value=your_price.market_value - total_expenses.market_value,
                     fact_value=your_price.market_value - total_expenses.market_value)
        data_indicators.append(profit)
        # ROS (доходность, рентабельность продаж)
        ros = Row(group, "ROS (доходность, рентабельность продаж)",
                  plan_value=profit.plan_value / your_price.plan_value,
                  market_value=your_price.market_value and profit.market_value / your_price.market_value,
                  fact_value=your_price.fact_value and profit.fact_value / your_price.fact_value)
        data_indicators.append(ros)
        # Наценка
        margin = Row(group, "Наценка", 
                     plan_value=your_price.plan_value - cost_price.plan_value,
                     market_value=your_price.market_value - cost_price.market_value,
                     fact_value=your_price.fact_value - cost_price.fact_value)
        data_indicators.append(margin)
        # Процент наценки
        margin_percent = Row(group, "Процент наценки",
                             plan_value=margin.plan_value / cost_price.plan_value,
                             market_value=margin.market_value / cost_price.market_value,
                             fact_value=margin.fact_value / cost_price.fact_value)
        data_indicators.append(margin_percent)
        # ROE (рентабельность инвестиций)
        roe = Row(group, "ROE (рентабельность инвестиций)",
                  plan_value=profit.plan_value / cost_price.plan_value,
                  market_value=profit.market_value / cost_price.market_value,
                  fact_value=profit.fact_value / cost_price.fact_value)
        data_indicators.append(roe)


        data = [i._asdict() for i in data_prices + 
                data_ozon_expenses + 
                data_company_expenses + 
                [tax] + 
                data_indicators]
        return data
    

    def update_for_products(self, products):
        products.price_comparison_ids.unlink()
        data = []
        for i, prod in enumerate(products):
            data.extend(self.collect_product_data(prod))
            print(f"{i} - price_comparison_ids were updated")
        self.create(data)
