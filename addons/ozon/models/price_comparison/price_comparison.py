from collections import namedtuple

from odoo import models, fields, api


class PriceComparison(models.Model):
    _name = "ozon.price_comparison"
    _description = "Сравнение цен"
    
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    price_component_id = fields.Many2one("ozon.price_component", string="Компонент цены")

    name = fields.Char(string="Показатель (статья расходов, индикатор)", 
                       related="price_component_id.name")
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
    def create_row_based_on_price_row(self, RowClass, price_row, group, name, coef, 
                                      price_component_id, max_val=0):
        if max_val == 0:
            plan_value = price_row.plan_value * coef
            market_value = price_row.market_value * coef
        else:
            plan_value = min(price_row.plan_value * coef, max_val)
            market_value = min(price_row.market_value * coef, max_val)
        row = RowClass(group=group, name=name,
                plan_value=plan_value,
                market_value=market_value,
                fact_value=0, price_component_id=price_component_id)
        return row
    
    def collect_product_data(self, product) -> list:
        """Collects all data needed to create price_comparison_ids for product."""
        p_id = product.id
        Row = namedtuple(
            "Row", 
            ["group", "name", "plan_value", "market_value", "fact_value", 
             "price_component_id", "product_id"], 
            defaults=[p_id])
        price_component_model = self.env["ozon.price_component"]
        ### Цены
        group = "Цены"
        # TODO: Цена для покупателя - откуда брать?
        name = "Цена для покупателя"
        price_component = price_component_model.get_or_create(name)
        buyer_price = Row(group, name, plan_value=0, market_value=0, fact_value=0, 
                          price_component_id=price_component.id)
        # TODO: Ваша цена. Откуда брать значения ПЛАН, рынок, ФАКТ?
        name = "Ваша цена"
        price_component = price_component_model.get_or_create(name)
        min_comp_price = product.get_minimal_competitor_price()
        fact_price = 0 # TODO
        your_price = Row(group, name, plan_value=product.price, 
                         market_value=min_comp_price, 
                         fact_value=fact_price, 
                         price_component_id=price_component.id)
        data_prices = [buyer_price, your_price]

        ### Расходы Ozon
        data_ozon_expenses = []
        group = "Расходы Ozon"
        # Себестоимость - fix
        name = "Себестоимость"
        price_component = price_component_model.get_or_create(name)
        cp = product.fix_expenses.filtered(lambda r: r.name == "Себестоимость товара").price
        if cp == 0:
            return [{"product_id": p_id, "comment": "Не задана себестоимость."}]
        cost_price = Row(group, name, cp, cp, cp, price_component.id)
        data_ozon_expenses.append(cost_price)
        # Логистика - fix
        name = "Логистика"
        price_component = price_component_model.get_or_create(name)
        log = product.all_expenses_ids.filtered(lambda r: r.category == name).value
        data_ozon_expenses.append(Row(group, name, log, log, log, price_component.id))
        # Последняя миля - percent
        name = "Последняя миля"
        price_component = price_component_model.get_or_create(name)
        lm = product.all_expenses_ids.filtered(lambda r: r.category == name).percent
        last_mile = self.create_row_based_on_price_row(Row, your_price, group, name, lm, 
                                                        price_component.id, max_val=500)
        data_ozon_expenses.append(last_mile)
        # Эквайринг - percent
        name = "Эквайринг"
        price_component = price_component_model.get_or_create(name)
        acq = product.all_expenses_ids.filtered(lambda r: r.category == name).percent
        acquiring = self.create_row_based_on_price_row(Row, your_price, group, name, acq, 
                                                       price_component.id)
        data_ozon_expenses.append(acquiring)
        # Вознаграждение Ozon (комиссия Ozon) - percent
        name = "Вознаграждение Ozon"
        price_component = price_component_model.get_or_create(name)
        com = product.all_expenses_ids.filtered(lambda r: r.category == name).percent
        commission = self.create_row_based_on_price_row(Row, your_price, group, name, com,
                                                        price_component.id)
        data_ozon_expenses.append(commission)
        # Реклама - percent
        name = "Реклама"
        price_component = price_component_model.get_or_create(name)
        promo_percent = product.all_expenses_ids.filtered(
            lambda r: r.name == "Средняя стоимость продвижения товара").percent
        promo = self.create_row_based_on_price_row(Row, your_price, group, name, promo_percent,
                                                   price_component.id)
        data_ozon_expenses.append(promo)
        # Обработка - fix
        name = "Обработка"
        price_component = price_component_model.get_or_create(name)
        proc = product.all_expenses_ids.filtered(lambda r: r.category == name).value
        data_ozon_expenses.append(Row(group, name, proc, proc, proc, price_component.id))
        # Обратная логистика - fix  TODO: depends on sales qty and returns
        name = "Обратная логистика"
        price_component = price_component_model.get_or_create(name)
        data_ozon_expenses.append(Row(group, name, 0, 0, 0, price_component.id))

        ### Расходы компании
        group = "Расходы компании"
        data_company_expenses = []
        # TODO переделать - брать значения из модели Конструктор цен
        name = "Обработка и хранение"
        price_component = price_component_model.get_or_create(name)
        data_company_expenses.append(Row(group, name, 0, 0, 0, price_component.id))
        name = "Упаковка"
        price_component = price_component_model.get_or_create(name)
        data_company_expenses.append(Row(group, name, 0, 0, 0, price_component.id))
        name = "Маркетинг"
        price_component = price_component_model.get_or_create(name)
        data_company_expenses.append(Row(group, name, 0, 0, 0, price_component.id))
        name = "Операторы"
        price_component = price_component_model.get_or_create(name)
        data_company_expenses.append(Row(group, name, 0, 0, 0, price_component.id))

        ### Налог
        # Налог - percent
        name, group = "Налог", "Налог"
        price_component = price_component_model.get_or_create(name)
        t_percent = product.all_expenses_ids.filtered(lambda r: r.name == name).percent
        tax = self.create_row_based_on_price_row(Row, your_price, group, name, t_percent,
                                                 price_component.id)

        ### Показатели
        group = "Показатели"
        data_indicators = []
        # Сумма расходов
        name = "Сумма расходов"
        price_component = price_component_model.get_or_create(name)
        pv, mv, fv = 0, 0, 0
        for i in data_ozon_expenses + data_company_expenses:
            pv += i.plan_value
            mv += i.market_value
            fv += i.fact_value
        total_expenses = Row(group, "Сумма расходов", pv, mv, fv, price_component.id)
        data_indicators.append(total_expenses)
        # Прибыль
        name = "Прибыль"
        price_component = price_component_model.get_or_create(name)
        profit = Row(group, name, 
                     plan_value=your_price.plan_value - total_expenses.plan_value,
                     market_value=your_price.market_value - total_expenses.market_value,
                     fact_value=your_price.market_value - total_expenses.market_value,
                     price_component_id=price_component.id)
        data_indicators.append(profit)
        # ROS (доходность, рентабельность продаж)
        name = "ROS (доходность, рентабельность продаж)"
        price_component = price_component_model.get_or_create(name)
        ros = Row(group, name,
                  plan_value=profit.plan_value / your_price.plan_value,
                  market_value=your_price.market_value and profit.market_value / your_price.market_value,
                  fact_value=your_price.fact_value and profit.fact_value / your_price.fact_value,
                  price_component_id=price_component.id)
        data_indicators.append(ros)
        # Наценка
        name = "Наценка"
        price_component = price_component_model.get_or_create(name)
        margin = Row(group, name, 
                     plan_value=your_price.plan_value - cost_price.plan_value,
                     market_value=your_price.market_value - cost_price.market_value,
                     fact_value=your_price.fact_value - cost_price.fact_value,
                     price_component_id=price_component.id)
        data_indicators.append(margin)
        # Процент наценки
        name = "Процент наценки"
        price_component = price_component_model.get_or_create(name)
        margin_percent = Row(group, name,
                             plan_value=margin.plan_value / cost_price.plan_value,
                             market_value=margin.market_value / cost_price.market_value,
                             fact_value=margin.fact_value / cost_price.fact_value,
                             price_component_id=price_component.id)
        data_indicators.append(margin_percent)
        # ROE (рентабельность инвестиций)
        name = "ROE (рентабельность инвестиций)"
        price_component = price_component_model.get_or_create(name)
        roe = Row(group, name,
                  plan_value=profit.plan_value / cost_price.plan_value,
                  market_value=profit.market_value / cost_price.market_value,
                  fact_value=profit.fact_value / cost_price.fact_value,
                  price_component_id=price_component.id)
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
