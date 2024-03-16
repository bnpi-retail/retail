import ast
import logging
from copy import copy
from typing import Iterable
from collections import defaultdict
from datetime import datetime, time, timedelta, date
from operator import itemgetter
from lxml import etree
from .drawing_graphs import DrawGraph as df
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(__name__)

from .indirect_percent_expenses import STRING_FIELDNAMES
from ..ozon_api import (
    MIN_FIX_EXPENSES_FBS,
    MAX_FIX_EXPENSES_FBS,
    MIN_FIX_EXPENSES_FBO,
    MAX_FIX_EXPENSES_FBO,
)

from ..helpers import (
    split_list,
    split_keywords,
    split_keywords_on_slash,
    remove_latin_characters,
    remove_duplicates_from_list,
    mean,
    delete_records
)


class Product(models.Model):
    _name = "ozon.products"
    _description = "Лоты"

    # GPT
    description = fields.Text(string="Описание товара")
    
    tracked_search_query_ids = fields.Many2many(
        'ozon.tracked_search_queries', 
        'product_tracked_search_rel', 
        'product_id', 
        'tracked_search_query_id', 
        string="Отслеживаемые поисковые запросы"
    )

    categories = fields.Many2one("ozon.categories", string="Категория")
    id_on_platform = fields.Char(string="Product ID", readonly=True, index=True)
    sku = fields.Char(string="SKU", readonly=True)
    fbo_sku = fields.Char(string="FBO SKU", readonly=True)
    fbs_sku = fields.Char(string="FBS SKU", readonly=True)
    article = fields.Char(string="Артикул", readonly=True)
    
    supplementary_categories = fields.Many2many(
        "ozon.supplementary_categories",
        string="Вспомогательные категории",
        readonly=True,
    )
    products = fields.Many2one("retail.products", string="Товар")
    price = fields.Float(string="Актуальная цена", readonly=True)
    marketing_price = fields.Float(string="Цена на товар с учетом всех акций", readonly=True)
    marketing_discount = fields.Float(string="Маркетинговая скидка Ozon",
                                      compute="_compute_marketing_discount")
    category_marketing_discount = fields.Float(string="Средняя маркетинговая скидка Ozon по категории*",
                                               related="categories.price_difference")
    calculator_delta = fields.Float(string="Дельта", compute="_compute_calculator_delta")
    calculator_profit_norm = fields.Float(string="Доходность", 
                                                 compute="_compute_calculator_profit_norm")
    calculator_investment = fields.Float(string="Investment", 
                                                 compute="_compute_calculator_investment")
    expected_price = fields.Float(string="Ожидаемая цена", compute="_compute_expected_price",
                                  readonly=False)
    expected_price_error = fields.Text(string="Комментарий к ожидаемой цене", readonly=True)
    price_delta = fields.Float(
        string="Разница между актуальной и ожидаемой ценой",
        readonly=True,
        compute="_compute_price_delta",
    )
    old_price = fields.Float(string="Цена до учёта скидок", readonly=True)
    ext_comp_min_price = fields.Float(
        string="Минимальная цена товара у конкурентов на другой площадке", readonly=True
    )
    ozon_comp_min_price = fields.Float(
        string="Минимальная цена товара у конкурентов на Ozon", readonly=True
    )
    self_marketplaces_min_price = fields.Float(
        string="Минимальная цена вашего товара на других площадках", readonly=True
    )
    price_index = fields.Selection(
        [
            ("WITHOUT_INDEX", "Без индекса"),
            ("PROFIT", "Выгодный"),
            ("AVG_PROFIT", "Умеренный"),
            ("NON_PROFIT", "Невыгодный"),
        ],
        string="Ценовой индекс",
        readonly=True,
    )

    imgs_urls = fields.Char(string="Ссылки на изображения")
    imgs_html = fields.Html(compute="_compute_imgs")
    seller = fields.Many2one("retail.seller", string="Продавец")
    insurance = fields.Float(string="Страховой коэффициент, %")
    search_queries = fields.One2many(
        "ozon.search_queries", "product_id", string="Ключевые слова"
    )
    trading_scheme = fields.Selection(
        [("FBS", "FBS"), ("FBO", "FBO"), ("FBS, FBO", "FBS, FBO"), ("undefined", " ")],
        string="Схема торговли",
    )

    delivery_location = fields.Selection(
        [
            ("PC", "ППЗ/PC"),
            ("PP", "ПВЗ/PP"),
            ("SC", "СЦ/SC"),
            ("TSC", "ТСЦ/TSC"),
            ("", ""),
        ],
        string="Пункт приема товара",
        help=(
            "ППЦ - Пункт приема заказов (Pickup Center), "
            "ПВЗ - Пункт выдачи заказов (Pickup Point), "
            "СЦ - Сервисный центр (Service Center)"
        ),
    )

    competitors_with_price_ids = fields.One2many(
        "ozon.price_history_competitors",
        "product_id",
        string="Актуальные цены конкурентов",
    )

    not_enough_competitors = fields.Boolean()
    commentary_not_enough_competitors = fields.Char()

    price_our_history_ids = fields.One2many(
        "ozon.price_history", "product_id", string="История цен"
    )
    stock_ids = fields.One2many("ozon.stock", "product", string="История остатков")
    stock_history_count = fields.Integer(compute="_compute_stock_history_count")
    stocks_fbs = fields.Integer(string="FBS остатки", readonly=True)
    stocks_fbo = fields.Integer(string="FBO остатки", readonly=True)
    is_selling = fields.Boolean(
        string="В продаже", compute="_get_is_selling", store=True, readonly=True
    )
    is_alive = fields.Boolean(string="Живой товар", readonly=True)
    is_participating_in_actions = fields.Boolean(
        string="Участвует в акциях", readonly=True
    )

    fix_expenses = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты",
        copy=True,
        readonly=True,
    )
    # FBO fix expenses
    fbo_fix_expenses_min = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты минимальные (FBO)",
        readonly=True,
        domain=[("name", "in", MIN_FIX_EXPENSES_FBO)],
    )
    total_fbo_fix_expenses_min = fields.Float(
        string="Итого", compute="_compute_total_fbo_fix_expenses_min", store=True
    )
    fbo_fix_expenses_max = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты максимальные (FBO)",
        readonly=True,
        domain=[("name", "in", MAX_FIX_EXPENSES_FBO)],
    )
    total_fbo_fix_expenses_max = fields.Float(
        string="Итого", compute="_compute_total_fbo_fix_expenses_max", store=True
    )
    # FBS fix expenses
    fbs_fix_expenses_min = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты минимальные (FBS)",
        readonly=True,
        domain=[("name", "in", MIN_FIX_EXPENSES_FBS)],
    )
    total_fbs_fix_expenses_min = fields.Float(
        string="Итого", compute="_compute_total_fbs_fix_expenses_min", store=True
    )
    fbs_fix_expenses_max = fields.One2many(
        "ozon.fix_expenses",
        "product_id",
        string="Фиксированные затраты максимальные (FBS)",
        readonly=True,
        domain=[("name", "in", MAX_FIX_EXPENSES_FBS)],
    )
    total_fbs_fix_expenses_max = fields.Float(
        string="Итого", compute="_compute_total_fbs_fix_expenses_max", store=True
    )

    percent_expenses = fields.One2many(
        "ozon.cost",
        "product_id",
        string="Процент от продаж",
        copy=True,
        readonly=True,
    )

    fbo_percent_expenses = fields.One2many(
        "ozon.cost",
        "product_id",
        string="Процент от продаж (FBO)",
        readonly=True,
        domain=[
            (
                "name",
                "in",
                [
                    "Процент комиссии за продажу (FBO)",
                    "Общий коэффициент косвенных затрат",
                ],
            )
        ],
    )
    total_fbo_percent_expenses = fields.Float(
        string="Итого", compute="_compute_total_fbo_percent_expenses", store=True
    )

    fbs_percent_expenses = fields.One2many(
        "ozon.cost",
        "product_id",
        string="Процент от продаж (FBS)",
        readonly=True,
        domain=[
            (
                "name",
                "in",
                [
                    "Процент комиссии за продажу (FBS)",
                    "Общий коэффициент косвенных затрат",
                ],
            )
        ],
    )
    total_fbs_percent_expenses = fields.Float(
        string="Итого", compute="_compute_total_fbs_percent_expenses", store=True
    )
    all_expenses_ids = fields.One2many(
        "ozon.all_expenses", "product_id", string="Все затраты", readonly=True
    )
    all_expenses_except_roi_roe_ids = fields.One2many(
        "ozon.all_expenses", "product_id", string="Все затраты", readonly=True,
        domain=[("name", "not in", ["Доходность", "Investment"]),
                ("expected_value", "!=", 0)]
    )
    all_expenses_only_roi_roe_ids = fields.One2many(
        "ozon.all_expenses", "product_id", string="Все затраты", readonly=True,
        domain=[("name", "in", ["Доходность", "Investment"])]
    )
    total_all_expenses_ids = fields.Float(
        string="Итого общих затрат, исходя из актуальной цены",
        compute="_compute_total_all_expenses_ids",
    )
    total_expected_price_all_expenses_ids = fields.Float(
        string="Итого общих затрат, исходя из ожидаемой цены",
        compute="_compute_total_expected_price_all_expenses_ids",
    )
    total_all_expenses_ids_except_tax_roe_roi = fields.Float(
        string="Итого общих затрат без налогов, ROE, ROI, исходя из актуальной цены",
        compute="_compute_total_all_expenses_ids_except_tax_roe_roi",
    )
    total_all_expenses_ids_except_roe_roi = fields.Float(
        string="Итого общих затрат без ROE, ROI, исходя из актуальной цены",
        compute="_compute_total_all_expenses_ids_except_roe_roi",
    )

    promotion_expenses_ids = fields.One2many(
        "ozon.promotion_expenses",
        "product_id",
        string="Затраты на продвижение",
        readonly=True,
    )
    product_fee = fields.Many2one("ozon.product_fee", string="Комиссии товара Ozon")
    posting_ids = fields.Many2many("ozon.posting", string="Отправления Ozon")
    postings_count = fields.Integer(compute="_compute_count_postings")
    fbo_supply_order_product_ids = fields.One2many(
        "ozon.fbo_supply_order_product", "product_id", string="Поставки"
    )
    supply_orders_count = fields.Integer(compute="_compute_supply_orders_count")
    sales = fields.One2many(
        "ozon.sale",
        "product",
        string="Продажи",
        copy=True,
        readonly=True,
    )
    sales_per_day_last_30_days = fields.Float(
        string="Среднее кол-во продаж в день за последние 30 дней",
    )
    sales_per_day_last_30_days_group = fields.Char(
        string="Группа коэффициента продаваемости",
    )
    investment_expenses_id = fields.Many2one(
        "ozon.investment_expenses", string="Investment"
    )
    profitability_norm = fields.Many2one(
        "ozon.profitability_norm", string="Доходность"
    )
    coef_profitability = fields.Float(
        string="Отклонение от прибыли",
    )
    coef_profitability_group = fields.Char(
        string="Группа отклонения от прибыли",
    )
    profit = fields.Float(
        string="Прибыль от актуальной цены", compute="_compute_profit"
    )
    profit_ideal = fields.Float(
        string="Идеальная прибыль", compute="_compute_profit_ideal"
    )
    profit_delta = fields.Float(
        string="Разница между прибылью и идеальной прибылью",
        compute="_compute_profit_delta",
    )
    calculated_pricing_strategy_ids = fields.One2many(
        "ozon.calculated_pricing_strategy", "product_id", string="Калькулятор стратегий"
    )
    product_calculator_ids = fields.One2many(
        "ozon.product_calculator",
        "product_id",
        string="Рассчитываемые параметры",
    )
    mass_pricing_ids = fields.One2many(
        "ozon.mass_pricing",
        "product",
        string="Товар в очереди на изменение цен",
    )
    is_button_create_mass_pricing_shown = fields.Boolean(
        compute="_compute_is_button_create_mass_pricing_shown"
    )
    get_sales_count = fields.Integer(compute="compute_count_sales")
    price_history_count = fields.Integer(compute="compute_count_price_history")
    promotion_expenses_count = fields.Integer(compute="compute_count_promotion_expenses")
    action_candidate_ids = fields.One2many(
        "ozon.action_candidate", "product_id", string="Кандидат в акциях"
    )
    # indicators
    ozon_products_indicator_ids = fields.One2many(
        "ozon.products.indicator", inverse_name="ozon_product_id"
    )
    ozon_products_indicators_summary_ids = fields.One2many(
        "ozon.products.indicator.summary", inverse_name="ozon_product_id"
    )

    ozon_products_indicator_qty = fields.Integer(
        compute="_compute_ozon_products_indicator_qty",
        store=True
    )
    retail_product_total_cost_price = fields.Float(
        compute="_compute_total_cost_price", store=True
    )
    # ABC analysis
    revenue_share_temp = fields.Float()
    revenue_cumulative_share_temp = fields.Float()
    abc_group = fields.Char(size=3)

    categories_to_tasks = defaultdict(lambda: defaultdict(str))

    # BCG matrix
    market_share = fields.Float(string="Доля рынка", digits=(12, 5))
    market_share_is_computed = fields.Boolean()
    bcg_group = fields.Selection([
        ('a', 'Звезда'), ('b', 'Дойная корова'), ('c', 'Проблема'), ('d', 'Собака'), ('e', 'Нет данных')
    ], default='e')
    bcg_group_is_computed = fields.Boolean()
    # revenue and expenses
    ozon_report_products_revenue_expenses_ids = fields.One2many(
        'ozon.report.products_revenue_expenses',
        'ozon_products_id',
    )
    ozon_report_products_revenue_expenses_theory_ids = fields.One2many(
        'ozon.report.products_revenue_expenses_theory',
        'ozon_products_id',
    )
    period_start = fields.Date(string="Период с", compute="_compute_period")
    period_finish = fields.Date(string="по")
    period_preset = fields.Selection([
        ('month', '1 месяц'), ('2month', '2 месяца'), ('3month', '3 месяца')
    ])
    avg_value_to_use = fields.Selection(
        [
            ('input', 'Использовать значения, введённые вручную'),
            ('category', 'Использовать значения по категории'),
            ('report', 'Использовать значения по магазину из последнего отчёта о выплатах'),
        ],
        default='input',
        string="Значения для расчета фактических статей затрат",
    )
    is_promotion_data_correct = fields.Boolean()
    # ----------------
    plan_calc_date = fields.Date(string="Дата расчёта (План)", readonly=True)
    fact_calc_date = fields.Date(string="Дата расчёта (Факт)", readonly=True)
    calc_column_your_price = fields.Float(string="""Цена в столбце "Калькулятор" """)
    price_comparison_ids = fields.One2many("ozon.price_comparison", "product_id", 
                                           string="Сравнение цен", readonly=True)
    base_calculation_ids = fields.One2many("ozon.base_calculation", "product_id", string="Плановая цена")
    base_calculation_template_id = fields.Many2one("ozon.base_calculation_template", 
                                                   string="Шаблон планового расчёта")
    logistics_tariff_id = fields.Many2one("ozon.logistics_tariff", 
                                          string="Тариф логистики в плановом расчёте")

    last_plots_update = fields.Datetime()
   

    @api.onchange('period_preset')
    def _onchange_period_preset(self):
        preset = self.period_preset
        period_to = date.today() - timedelta(days=1)
        period_from = period_from = period_to - timedelta(days=30.5)
        if preset:
            if preset == 'month':
                period_from = period_to - timedelta(days=30.5)
            elif preset == '2month':
                period_from = period_to - timedelta(days=61)
            elif preset == '3month':
                period_from = period_to - timedelta(days=91.5)

        self.period_start = period_from
        self.period_finish = period_to

    def _compute_period(self):
        report = self.env["ozon.indirect_percent_expenses"].get_latest()
        if report:
            self.period_start = report.date_from
            self.period_finish = report.date_to
            self.period_preset = False

    def action_calculate_revenue_returns_promotion_for_period(self):
        delete_records(
            'ozon_report_products_revenue_expenses',
            self.ozon_report_products_revenue_expenses_ids.ids, self.env)
        delete_records(
            'ozon_report_products_revenue_expenses_theory',
            self.ozon_report_products_revenue_expenses_theory_ids.ids, self.env)
        vals_to_write_table_1 = []
        vals_to_write_table_2 = []
        # revenue
        res = self.calculate_sales_revenue_for_period()
        vals_table_1, vals_table_2, revenue, category_revenue, total_revenue = res
        vals_to_write_table_1.append(vals_table_1)
        vals_to_write_table_2.append(vals_table_2)

        # promotion_expenses
        vals_to_write_table_1.append(
            self.calculate_promotion_expenses_for_period(revenue, total_revenue, category_revenue))

        # returns
        vals_to_write_table_1.append(
            self.calculate_expenses_row(
                revenue=revenue,
                total_revenue=total_revenue,
                category_revenue=category_revenue,
                identifier=3,
                plan_name='Обратная логистика',
            )
        )
        # commission
        vals_to_write_table_2.append(
            self.calculate_commissions_row(
                revenue=revenue,
                category_revenue=category_revenue,
                identifier=2,
                plan_name='Вознаграждение Ozon',
            )
        )
        # equiring
        vals_to_write_table_2.append(
            self.calculate_commissions_row(
                revenue=revenue,
                category_revenue=category_revenue,
                identifier=3,
                plan_name='Эквайринг',
            )
        )

        self.env['ozon.report.products_revenue_expenses'].create(vals_to_write_table_1)
        self.env['ozon.report.products_revenue_expenses_theory'].create(vals_to_write_table_2)

    def get_sum_value_and_qty_from_transaction_value_by_product(
            self, name: str,
            ids: Iterable = None,
            start: date = None,
            finish: date = None
    ) -> tuple:

        if ids is None:
            ids = (self.id, )
        if start is None:
            start = self.period_start
        if finish is None:
            finish = self.period_finish
        query = """
                SELECT
                    SUM(value) as sum_value,
                    COUNT(*) as qty
                FROM 
                    ozon_transaction_value_by_product
                WHERE 
                    transaction_date >= %s
                    AND
                    transaction_date <= %s
                    AND
                    ozon_products_id IN %s
                    AND
                    name = %s
                """
        self.env.cr.execute(query, (start, finish, tuple(ids), name))
        sum_value_and_qty = self.env.cr.fetchone()
        sum_value = sum_value_and_qty[0] if sum_value_and_qty and sum_value_and_qty[0] else 0
        qty = sum_value_and_qty[1] if sum_value_and_qty else 0

        return sum_value, qty

    def calculate_sales_revenue_for_period(self) -> tuple[dict, dict, float, float, float]:
        revenue, sales_qty = self.get_sum_value_and_qty_from_transaction_value_by_product('Сумма за заказы')
        category_products_ids = self.categories.ozon_products_ids.ids
        category_revenue, cat_qty = self.get_sum_value_and_qty_from_transaction_value_by_product(
            name='Сумма за заказы',
            ids=category_products_ids
        )
        total_revenue = self.calc_total_sum('Сумма за заказы')
        vals_table_1 = {
            'identifier': 1,
            'ozon_products_id': self.id,
            'name': 'Выручка за период',
            'comment': 'Рассчитывается сложением значений поля "Значение" записей в меню '
                       '"Декомпозированные транзакции" '
                       'за искомый период, соответствующих текущему продукту и с названием '
                       '"Сумма за заказы".',
            'qty': sales_qty,
            'percent': 100,
            'value': revenue,
            'percent_from_total': 100,
            'percent_from_total_category': 100,
            'total_value_category': category_revenue,
            'total_value': total_revenue,
        }
        vals_table_2 = {
            'identifier': 1,
            'ozon_products_id': self.id,
            'name': 'Выручка за период',
            'comment': 'Рассчитывается сложением значений поля "Значение" записей в меню '
                       '"Декомпозированные транзакции" '
                       'за искомый период, соответствующих текущему продукту и с названием '
                       '"Сумма за заказы".',
            'qty': sales_qty,
            'percent': 100,
            'value': revenue,
            'percent_from_total_category': 100,
            'total_value_category': category_revenue,
            'theoretical_value': '',
        }

        return vals_table_1, vals_table_2, revenue, category_revenue, total_revenue

    def calculate_promotion_expenses_for_period(
            self, revenue: float, total_revenue: float, category_revenue: float
    ) -> dict:
        promotion_expenses = self.promotion_expenses_ids
        promotion_expenses_for_period = sum(
            pe.expense for pe in promotion_expenses if self.period_finish >= pe.date >= self.period_start
        )
        category_products = self.categories.ozon_products_ids
        category_pe_for_period = sum(sum(
            pe.expense for pe in product.promotion_expenses_ids if self.period_finish >= pe.date >= self.period_start
        ) for product in category_products)

        percent = (promotion_expenses_for_period * 100) / revenue if revenue else 0
        percent_category = (category_pe_for_period * 100) / category_revenue if category_revenue else 0
        total_promotion_expenses = self.calc_total_sum('Услуги продвижения товаров')
        percent_from_total = (abs(total_promotion_expenses) * 100) / total_revenue if total_revenue else 0

        accuracy = self.calc_accuracy(self.period_start, self.period_finish)
        self.is_promotion_data_correct = True if accuracy == 'a' else False
        name = 'Расходы на продвижение продукта за период'
        if accuracy == 'c':
            name = 'Расходы на продвижение продукта за период*'

        return {
            'identifier': 2,
            'ozon_products_id': self.id,
            'name': name,
            'comment': 'Рассчитывается сложением суммы значений поля "Расход" '
                       'затрат на продвижение текущего товара за искомый период.\n',
            'value': -promotion_expenses_for_period,
            'qty': len(promotion_expenses),
            'percent': percent,
            'percent_from_total': percent_from_total,
            'total_value': total_promotion_expenses,
            'percent_from_total_category': percent_category,
            'total_value_category': -category_pe_for_period,
            'accuracy': accuracy,
        }

    def calc_accuracy(self, period_start, period_finish) -> str:
        ps = period_start
        pf = period_finish
        query = """
                SELECT
                    period_start_date,
                    period_end_date
                FROM 
                    ozon_import_file
                WHERE 
                    data_for_download = %s
                    AND
                    period_start_date IS NOT NULL
                    AND
                    period_end_date IS NOT NULL
                ORDER BY
                    period_start_date
                """
        self.env.cr.execute(query, ('ozon_ad_campgaign_search_promotion_report', ))
        imports_periods = self.env.cr.fetchall()
        is_covered = False
        if imports_periods:
            joined_periods = []
            start = end = None
            for s, e in imports_periods:
                if not start:
                    start = s
                    end = e
                if start <= s <= end + timedelta(days=1):
                    end = max(end, e)
                else:
                    joined_periods.append((start, end))
                    start = s
                    end = e
                if s == imports_periods[-1][0] and e == imports_periods[-1][1]:
                    joined_periods.append((start, end))

            joined_periods.reverse()

            for start, end in joined_periods:
                if start <= ps <= end:
                    if start <= pf <= end:
                        is_covered = True
                        break

        accuracy = 'a' if is_covered else 'c'

        return accuracy

    def calculate_expenses_row(
            self, revenue: float, total_revenue: float, category_revenue: float, identifier: int,
            plan_name: str) -> dict:

        ozon_price_component_id = self.env["ozon.price_component"].search([('name', '=', plan_name)]).id
        if not ozon_price_component_id:
            raise UserError("Создайте справочник фактических и плановых статей затрат в Планировании"
                            f" в котором плановым будет запись {plan_name}")
        ozon_price_component_match = self.env["ozon.price_component_match"].search([
            ('price_component_id', '=', ozon_price_component_id)
        ])
        total_amount_ = 0
        qty = []
        category_amount = 0
        all_products_amount = 0
        components = []
        category_products_ids = self.categories.ozon_products_ids.ids
        for record in ozon_price_component_match:
            name = record.name
            res = self.get_sum_value_and_qty_from_transaction_value_by_product(name)
            category_value, cat_qty = self.get_sum_value_and_qty_from_transaction_value_by_product(
                name=name,
                ids=category_products_ids
            )
            category_amount += category_value
            total_amount_ += res[0]
            qty.append(res[1])
            components.append(f"{name}: количество- {res[1]}, значение-{res[0]}\n")

            all_products_amount += self.calc_total_sum(name)

        qty = max(qty) if qty else 0
        components = ''.join(components)
        percent = (abs(total_amount_) * 100) / revenue if revenue else 0
        percent_category = (abs(category_amount) * 100) / category_revenue if category_revenue else 0
        percent_from_total = (abs(all_products_amount) * 100) / total_revenue if total_revenue else 0
        vals = {
            'identifier': identifier,
            'ozon_products_id': self.id,
            'name': plan_name,
            'comment': 'Рассчитывается суммированием значений записей "Декомпозированые транзакции" '
                       'с названиями указанными в поле "Фактическая статья затрат Ozon" напротив '
                       f'которых указано значение {plan_name} '
                       '(в меню Планирование > Фактические/плановые статьи). '
                       'Суммируются "Декомпозированые транзакции" соответствующие искомому периоду и '
                       f'текущему продукту\n\n{components}',
            'value': total_amount_,
            'qty': qty,
            'percent': percent,
            'percent_from_total': percent_from_total,
            'total_value': all_products_amount,
            'percent_from_total_category': percent_category,
            'total_value_category': category_amount,
        }
        return vals

    def calculate_commissions_row(
            self, revenue: float, category_revenue: float, identifier: int,
            plan_name: str) -> dict:

        ozon_price_component_id = self.env["ozon.price_component"].search([('name', '=', plan_name)]).id
        if not ozon_price_component_id:
            raise UserError("Создайте справочник фактических и плановых статей затрат в Планировании"
                            f" в котором плановым будет запись {plan_name}")
        ozon_price_component_match = self.env["ozon.price_component_match"].search([
            ('price_component_id', '=', ozon_price_component_id)
        ])
        total_amount_ = 0
        qty = []
        category_amount = 0
        components = []
        category_products_ids = self.categories.ozon_products_ids.ids
        for record in ozon_price_component_match:
            name = record.name
            res = self.get_sum_value_and_qty_from_transaction_value_by_product(name)
            category_value, cat_qty = self.get_sum_value_and_qty_from_transaction_value_by_product(
                name=name,
                ids=category_products_ids
            )
            category_amount += category_value
            total_amount_ += res[0]
            qty.append(res[1])
            components.append(f"{name}: количество- {res[1]}, значение-{res[0]}\n")

        qty = max(qty) if qty else 0
        components = ''.join(components)
        percent = (abs(total_amount_) * 100) / revenue if revenue else 0
        percent_category = (abs(category_amount) * 100) / category_revenue if category_revenue else 0
        theoretical_value = self.get_theoretical_value(plan_name)
        if plan_name == "Эквайринг":
            if qty and theoretical_value:
                theoretical_value = str(round((float(theoretical_value) * 100) / (revenue / qty), 2)) + '% максимально'
            else:
                pass

        vals = {
            'identifier': identifier,
            'ozon_products_id': self.id,
            'name': plan_name,
            'comment': 'Рассчитывается суммированием значений записей "Декомпозированые транзакции" '
                       'с названиями указанными в поле "Фактическая статья затрат Ozon" напротив '
                       f'которых указано значение {plan_name} '
                       '(в меню Планирование > Фактические/плановые статьи). '
                       'Суммируются "Декомпозированые транзакции" соответствующие искомому периоду и '
                       f'текущему продукту\n\n{components}',
            'value': total_amount_,
            'qty': qty,
            'percent': percent,
            'percent_from_total_category': percent_category,
            'total_value_category': category_amount,
            'theoretical_value': theoretical_value,
        }
        return vals

    def get_theoretical_value(self, plan_name: str, data_to_calc_value=None) -> str:
        value = ""
        trading_scheme = self.trading_scheme
        if plan_name == 'Вознаграждение Ozon':
            if trading_scheme == "FBS":
                for rec in self.fbs_percent_expenses:
                    if rec.name == "Процент комиссии за продажу (FBS)":
                        value = rec.discription
                        break
            elif trading_scheme == "FBO":
                for rec in self.fbo_percent_expenses:
                    if rec.name == "Процент комиссии за продажу (FBO)":
                        value = rec.discription
                        break
            else:
                fbs = ''
                for rec in self.fbs_percent_expenses:
                    if rec.name == "Процент комиссии за продажу (FBS)":
                        fbs = rec.discription
                        break
                fbo = ''
                for rec in self.fbo_percent_expenses:
                    if rec.name == "Процент комиссии за продажу (FBO)":
                        fbo = rec.discription
                        break
                if fbs and fbo:
                    fbs = fbs.replace('%', '')
                    fbo = fbo.replace('%', '')
                    fbs = float(fbs)
                    fbo = float(fbo)
                    value = max(fbs, fbo)
                    value = str(value) + '%'
                elif fbs:
                    value = fbs
                elif fbo:
                    value = fbo
        elif plan_name == "Эквайринг":
            if trading_scheme == "FBS":
                for rec in self.fbs_fix_expenses_max:
                    if rec.name == "Максимальная комиссия за эквайринг":
                        value = rec.price
                        break
            elif trading_scheme == "FBO":
                for rec in self.fbo_fix_expenses_max:
                    if rec.name == "Максимальная комиссия за эквайринг":
                        value = rec.price
                        break
            else:
                fbs = ''
                for rec in self.fbs_fix_expenses_max:
                    if rec.name == "Максимальная комиссия за эквайринг":
                        fbs = rec.price
                        break
                fbo = ''
                for rec in self.fbo_fix_expenses_max:
                    if rec.name == "Максимальная комиссия за эквайринг":
                        fbo = rec.price
                        break
                if fbs and fbo:
                    fbs = float(fbs)
                    fbo = float(fbo)
                    value = max(fbs, fbo)
                elif fbs:
                    value = fbs
                elif fbo:
                    value = fbo

        return value

    def calc_total_sum(self, name: str, start: date = None, finish: date = None):
        if start is None:
            start = self.period_start
        if finish is None:
            finish = self.period_finish
        query = """
                SELECT
                    SUM(value) as total_sum_value
                FROM 
                    ozon_transaction_value_by_product
                WHERE 
                    transaction_date >= %s
                    AND
                    transaction_date <= %s
                    AND
                    name = %s
                """
        self.env.cr.execute(query, (start, finish, name))
        total_sum_value = self.env.cr.fetchone()
        return total_sum_value[0] if total_sum_value and total_sum_value[0] else 0

    def get_products_and_skus_from_transaction_skus(self, skus: str) -> tuple[list, list]:
        products = []
        skus = skus.replace('[', '').replace(']', '')
        if skus:
            skus = skus.split(', ')
            for sku in skus:
                product = self.env['ozon.products'].search(
                    ["|", "|", ("sku", "=", sku), ("fbo_sku", "=", sku), ("fbs_sku", "=", sku)],
                )
                if product:
                    products.append(product)
        return products, skus

    def calculate_expected_price(self):
        # TODO: откуда берем ожидаемую цену?
        # ожид.цена=фикс.затраты/(1-процент_затрат-ожид.ROS-проц.налог-ожид.ROI)
        for rec in self:
            all_fix_expenses = rec.all_expenses_ids.filtered(lambda r: r.kind == "fix")
            sum_fix_expenses = sum(all_fix_expenses.mapped("value"))
            all_per_expenses = rec.all_expenses_ids.filtered(
                lambda r: r.kind == "percent"
            )
            total_percent = sum(all_per_expenses.mapped("percent"))
            if total_percent <= 1:
                rec.expected_price = sum_fix_expenses / (1 - total_percent)
            else:
                rec.expected_price = 0
                rec.expected_price_error = ("Невозможно рассчитать ожидаемую цену. "
                                "Задайте другое значение "
                                "ожидаемой доходности и/или Investment.")
            print(f"Product {rec.id} expected price was calculated")

    def _compute_price_delta(self):
        for rec in self:
            rec.price_delta = rec.price - rec.expected_price

    @api.depends("products.total_cost_price")
    def _compute_total_cost_price(self):
        for record in self:
            total_cost_prise = record.products.total_cost_price
            record.retail_product_total_cost_price = total_cost_prise
            record._check_cost_price(record)

    @api.depends("sales")
    def compute_count_sales(self):
        for record in self:
            record.get_sales_count = len(record.sales)

    def get_sales(self):
        self.ensure_one()

        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90)

        return {
            "type": "ir.actions.act_window",
            "name": "История продаж",
            "view_mode": "tree,graph",
            "res_model": "ozon.sale",
            "domain": [
                ("product", "=", self.id),
                ("date", ">=", three_months_ago.strftime("%Y-%m-%d %H:%M:%S")),
            ],
            "context": {
                "create": False,
                "views": [(False, "tree"), (False, "form"), (False, "graph")],
                "graph_mode": "line",
                "measure": "revenue",
                "interval": "day",
            },
        }

    @api.depends("price_our_history_ids")
    def compute_count_price_history(self):
        for record in self:
            record.price_history_count = len(record.price_our_history_ids)

    def history_price(self):
        self.ensure_one()

        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90)

        return {
            "type": "ir.actions.act_window",
            "name": "История цен",
            "view_mode": "tree,graph",
            "res_model": "ozon.price_history",
            "domain": [
                ("product_id", "=", self.id),
                ("timestamp", ">=", three_months_ago.strftime("%Y-%m-%d %H:%M:%S")),
            ],
            "context": {
                "create": False,
                "views": [(False, "tree"), (False, "form"), (False, "graph")],
                "graph_mode": "line",
                "measure": "profit",
                "interval": "day",
            },
        }

    def smart_action_promotion_expenses(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Затраты на продвижение",
            "view_mode": "tree",
            "res_model": "ozon.promotion_expenses",
            "domain": [
                ("product_id", "=", self.id),
            ],
            "context": {
                "create": False,
                "views": [(False, "tree"), (False, "form"), (False, "graph")],
            },
        }

    @api.depends('promotion_expenses_ids')
    def compute_count_promotion_expenses(self):
        self.promotion_expenses_count = len(self.promotion_expenses_ids) if self.promotion_expenses_ids else 0

    def _compute_profit(self):
        for rec in self:
            rec.profit = rec.price - rec.total_all_expenses_ids_except_tax_roe_roi

    @api.depends("price", "profitability_norm.value")
    def _compute_profit_ideal(self):
        for record in self:
            if record.profitability_norm:
                record.profit_ideal = record.price * record.profitability_norm.value
            else:
                record.profit_ideal = record.price * 0.2

    @api.depends("profit", "profit_ideal")
    def _compute_profit_delta(self):
        for record in self:
            record.profit_delta = record.profit - record.profit_ideal

    @api.depends("fbo_fix_expenses_min.price")
    def _compute_total_fbo_fix_expenses_min(self):
        for record in self:
            record.total_fbo_fix_expenses_min = sum(
                record.fbo_fix_expenses_min.mapped("price")
            )

    @api.depends("fbo_fix_expenses_max.price")
    def _compute_total_fbo_fix_expenses_max(self):
        for record in self:
            record.total_fbo_fix_expenses_max = sum(
                record.fbo_fix_expenses_max.mapped("price")
            )

    @api.depends("fbs_fix_expenses_min.price")
    def _compute_total_fbs_fix_expenses_min(self):
        for record in self:
            record.total_fbs_fix_expenses_min = sum(
                record.fbs_fix_expenses_min.mapped("price")
            )

    @api.depends("fbs_fix_expenses_max.price")
    def _compute_total_fbs_fix_expenses_max(self):
        for record in self:
            record.total_fbs_fix_expenses_max = sum(
                record.fbs_fix_expenses_max.mapped("price")
            )

    @api.depends("fbo_percent_expenses.price")
    def _compute_total_fbo_percent_expenses(self):
        for record in self:
            record.total_fbo_percent_expenses = sum(
                record.fbo_percent_expenses.mapped("price")
            )

    @api.depends("fbs_percent_expenses.price")
    def _compute_total_fbs_percent_expenses(self):
        for record in self:
            record.total_fbs_percent_expenses = sum(
                record.fbs_percent_expenses.mapped("price")
            )

    def _compute_total_all_expenses_ids(self):
        for rec in self:
            rec.total_all_expenses_ids = sum(rec.all_expenses_ids.mapped("value"))

    def _compute_total_expected_price_all_expenses_ids(self):
        for rec in self:
            rec.total_expected_price_all_expenses_ids = sum(
                rec.all_expenses_ids.mapped("expected_value")
            )

    def _compute_total_all_expenses_ids_except_tax_roe_roi(self):
        for rec in self:
            all_expenses_except_tax_roe_roi = rec.all_expenses_ids.filtered(
                lambda r: r.category not in ["Рентабельность", "Налоги", "Investment"]
            )
            total_expenses = sum(all_expenses_except_tax_roe_roi.mapped("value"))
            rec.total_all_expenses_ids_except_tax_roe_roi = total_expenses

    def _compute_total_all_expenses_ids_except_roe_roi(self):
        for rec in self:
            all_expenses_except_roe_roi = rec.all_expenses_ids.filtered(
                lambda r: r.category not in ["Рентабельность", "Investment"]
            )
            rec.total_all_expenses_ids_except_roe_roi = sum(
                all_expenses_except_roe_roi.mapped("value")
            )

    @api.depends("price_our_history_ids.price")
    def _compute_price_history_values(self):
        for product in self:
            product.price_history_values = [
                (record.timestamp, record.price)
                for record in product.price_our_history_ids
            ]

    @api.depends("sales")
    def _compute_sales_per_day_last_30_days(self):
        for product in self:
            date_from = datetime.combine(datetime.now(), time.min) - timedelta(days=30)
            date_to = datetime.combine(datetime.now(), time.max) - timedelta(days=1)
            # взять все продажи за посл 30 дней
            sales = self.env["ozon.sale"].search(
                [
                    ("product", "=", product.id),
                    ("date", ">", date_from),
                    ("date", "<", date_to),
                ]
            )
            # суммировать qty всех продаж
            total_qty = sum(sales.mapped("qty"))
            # делить эту сумму на 30
            product.sales_per_day_last_30_days = total_qty / 30

    def _compute_sales_per_day_last_30_days_group(self):
        coefs = self.read(fields=["sales_per_day_last_30_days"])
        coefs = sorted(coefs, key=itemgetter("sales_per_day_last_30_days"))
        if coefs:
            g1, g2, g3, g4, g5 = list(split_list(coefs, 5))
            for i, g in enumerate([g1, g2, g3, g4, g5]):
                g_min = round(g[0]["sales_per_day_last_30_days"], 2)
                g_max = round(g[-1]["sales_per_day_last_30_days"], 2)
                for item in g:
                    prod = self.env["ozon.products"].search([("id", "=", item["id"])])
                    prod.sales_per_day_last_30_days_group = (
                        f"Группа {i+1}: от {g_min} до {g_max}"
                    )

    @api.onchange("profit_delta", "profit_ideal")
    @api.depends("profit_delta", "profit_ideal")
    def _compute_coef_profitability(self):
        for product in self:
            if product.profit_ideal:
                product.coef_profitability = round(
                    product.profit_delta / product.profit_ideal, 2
                )
            else:
                product.coef_profitability = 0

    def _compute_coef_profitability_group(self):
        coefs = self.read(fields=["coef_profitability"])
        coefs = sorted(coefs, key=itemgetter("coef_profitability"))
        if coefs:
            g1, g2, g3, g4, g5 = list(split_list(coefs, 5))
            for i, g in enumerate([g1, g2, g3, g4, g5]):
                g_min = round(g[0]["coef_profitability"], 2)
                g_max = round(g[-1]["coef_profitability"], 2)
                for item in g:
                    prod = self.env["ozon.products"].search([("id", "=", item["id"])])
                    prod.coef_profitability_group = (
                        f"Группа {i+1}: от {g_min*100}% до {g_max*100}%"
                    )

    @api.model
    def create(self, values):
        existing_record = self.search(
            [("id_on_platform", "=", values.get("id_on_platform"))]
        )
        if existing_record:
            return existing_record

        records = super(Product, self).create(values)
        for record in records:
            self._check_cost_price(record, summary_update=False)
            self._check_investment_expenses(record, summary_update=False)
            self._check_profitability_norm(record, summary_update=False)
            self._check_competitors_with_price_ids_qty(record, summary_update=False)
            self._update_in_out_stock_indicators(record, summary_update=False)

            self.update_indicator_summary(record)

        return records

    def create_update_fix_exp_cost_price(self):
        for i, rec in enumerate(self):
            total_cost_price = rec.products.total_cost_price
            fix_exp_cost_price = rec.fix_expenses.filtered(
                lambda r: r.name == "Себестоимость товара"
            )
            if fix_exp_cost_price:
                fix_exp_cost_price.write({"price": total_cost_price})
                print(f'{i} - Fix expense "Себестоимость товара" was updated')
            else:
                fix_exp_cost_price = self.env["ozon.fix_expenses"].create(
                    {
                        "name": "Себестоимость товара",
                        "price": total_cost_price,
                        "discription": "Общая себестоимость товара",
                        "product_id": rec.id,
                    }
                )
                print(f'{i} - Fix expense "Себестоимость товара" was created')

    def _compute_expected_price(self):
        for r in self:
            r.expected_price = r.price


    @api.onchange("expected_price")
    def onchange_expected_price(self):
        exp_price = self.expected_price
        for i in self.all_expenses_ids:
            if i.kind == "fix":
                continue
            i.expected_value = i.percent * exp_price
            i._compute_comment()
        all_exp_profit_norm = self.all_expenses_only_roi_roe_ids.filtered(
                lambda r: r.name == "Доходность"
            )
        all_exp_invest = self.all_expenses_only_roi_roe_ids.filtered(
                lambda r: r.name == "Investment"
            )
        delta = exp_price - sum(self.all_expenses_except_roi_roe_ids.mapped("expected_value"))
        self.calculator_delta = delta
        if exp_price != 0:
            all_exp_profit_norm.percent = delta / exp_price
            all_exp_profit_norm.expected_value = all_exp_profit_norm.percent * exp_price
            all_exp_invest.percent = all_exp_profit_norm.percent / 2
            all_exp_invest.expected_value = all_exp_invest.percent * exp_price
        else:
            all_exp_profit_norm.percent = 0
            all_exp_profit_norm.expected_value = 0
            all_exp_invest.percent = 0
            all_exp_invest.expected_value = 0

        all_exp_profit_norm._compute_comment()
        all_exp_invest._compute_comment()

    def write(self, values, **kwargs):
        if values.get("profitability_norm") or values.get("investment_expenses_id"):
            self.update_current_product_all_expenses(expected_price=self.expected_price)
            self.calculate_expected_price()
            self.update_current_product_all_expenses(expected_price=self.expected_price)
        elif values.get("expected_price"):
            exp_price = self.expected_price
            self.update_current_product_all_expenses(expected_price=exp_price)
            all_exp_profit_norm = self.all_expenses_only_roi_roe_ids.filtered(
                    lambda r: r.name == "Доходность"
                )
            all_exp_invest = self.all_expenses_only_roi_roe_ids.filtered(
                    lambda r: r.name == "Investment"
                )
            delta = exp_price - sum(self.all_expenses_except_roi_roe_ids.mapped("expected_value"))
            values["calculator_delta"] = delta
            if exp_price != 0:
                all_exp_profit_norm.percent = delta / exp_price
                all_exp_profit_norm.expected_value = all_exp_profit_norm.percent * exp_price
                all_exp_invest.percent = all_exp_profit_norm.percent / 2
                all_exp_invest.expected_value = all_exp_invest.percent * exp_price
            else:
                all_exp_profit_norm.percent = 0
                all_exp_profit_norm.expected_value = 0
                all_exp_invest.percent = 0
                all_exp_invest.expected_value = 0

        if isinstance(values, dict) and values.get("fix_expenses"):
            fix_exp_cost_price = self.fix_expenses.filtered(
                lambda r: r.name == "Себестоимость товара"
            )
            if fix_exp_cost_price:
                values["fix_expenses"] = [fix_exp_cost_price.id] + values[
                    "fix_expenses"
                ]
            per_exp_recs = kwargs.get("percent_expenses")
            names = [rec.name for rec in per_exp_recs]
            for per_exp in self.percent_expenses:
                if per_exp.name not in names:
                    values["percent_expenses"].append(per_exp.id)

        res = super(Product, self).write(values)
        if values.get("not_enough_competitors"):
            self._not_enough_competitors_write(self)
        if (
            values.get("competitors_with_price_ids")
            or values.get("competitors_with_price_ids") is False
        ):
            self._check_competitors_with_price_ids_qty(self)
        if (
            values.get("investment_expenses_id")
            or values.get("investment_expenses_id") is False
        ):
            self._check_investment_expenses(self)
        if (
            values.get("profitability_norm")
            or values.get("profitability_norm") is False
        ):
            self._check_profitability_norm(self)

        return res

    @staticmethod
    def _get_indicators_and_summaries_types(record) -> tuple:
        self_indicators = record.ozon_products_indicator_ids
        indicator_types = defaultdict()
        for indicator in self_indicators:
            indicator_types[indicator.type] = indicator
        summary_types = defaultdict()
        for summary in record.ozon_products_indicators_summary_ids:
            summary_types[summary.type] = summary

        return indicator_types, summary_types

    def update_indicator_summary(self, record):
        indicator_types, summary_types = self._get_indicators_and_summaries_types(record)
        if indicator_types:
            ids_to_delete = []
            # cost price, investment, profitability_norm
            self._update_cost_price_investment_profitability_norm_indicators_summary(
                record, indicator_types, summary_types
            )
            # less 3 competitors
            self._update_less_3_competitors_indicator_summary(record, indicator_types, summary_types)
            # остатки
            self._update_in_out_indicator_summary(record, indicator_types, summary_types)
            # bcg
            summary_id = self._update_bcg_group_indicator_summary(record, indicator_types, summary_types)
            if summary_id:
                ids_to_delete.append(summary_id)
            # abc
            summary_id = self._update_abc_group_indicator_summary(record, indicator_types, summary_types)
            if summary_id:
                ids_to_delete.append(summary_id)

            query = """
                        DELETE FROM ozon_products_indicator_summary
                        WHERE id IN %s
                    """
            if ids_to_delete:
                self.env.cr.execute(query, (tuple(ids_to_delete),))
                logger.warning(f"delete from ozon_products_indicator_summary records with ids {ids_to_delete}")

    def _update_cost_price_investment_profitability_norm_indicators_summary(
            self, record, indicator_types=None, summary_types=None
    ):
        if not indicator_types and not summary_types:
            indicator_types, summary_types = self._get_indicators_and_summaries_types(record)

        indicator_cost_price = indicator_types.get("cost_not_calculated")
        indicator_investment = indicator_types.get("no_investment_expenses")
        indicator_profitability_norm = indicator_types.get("no_profitability_norm")
        common_indicator = False
        words = []
        days = 0
        for ind in (
                indicator_investment,
                indicator_cost_price,
                indicator_profitability_norm,
        ):
            if ind:
                common_indicator = True
                ind_days = (datetime.now() - ind.create_date).days
                if days < ind_days:
                    days = ind_days
        if indicator_cost_price:
            words.append("себестоимость не подсчитана, ")
        if indicator_investment:
            words.append("investment не установлен, ")
        if indicator_profitability_norm:
            words.append("ожидаемая доходность не установлена, ")

        if common_indicator:
            text = "".join(words)
            text = text.capitalize()[:-2]
            summary = summary_types.get("cost_not_calculated")
            if summary:
                summary.name = (
                    f"{text} дней: {days}. "
                    f"Точность расчета цены может быть снижена."
                )
            else:
                self.env["ozon.products.indicator.summary"].create(
                    {
                        "name": f"{text} дней: {days}. "
                                f"Точность расчета цены может быть снижена.",
                        "type": "cost_not_calculated",
                        "ozon_product_id": record.id,
                    }
                )

        else:
            summary = summary_types.get("cost_not_calculated")
            if summary:
                record.ozon_products_indicators_summary_ids = [(2, summary.id, 0)]

    def _update_less_3_competitors_indicator_summary(self, record, indicator_types=None, summary_types=None):
        if not indicator_types:
            indicator_types, summary_types = self._get_indicators_and_summaries_types(record)

        indicator_no_competitor_r = indicator_types.get("no_competitor_robot")
        indicator_no_competitor_m = indicator_types.get("no_competitor_manager")
        if indicator_no_competitor_r and not indicator_no_competitor_m:
            days = (datetime.now() - indicator_no_competitor_r.create_date).days
            summary = summary_types.get("no_competitor_robot")
            if summary:
                summary.name = (
                    f"Продукт имеет менее 3х конкурентов в течение дней: {days}. "
                    f"Цена не может быть рассчитана. Добавьте товары конкурентов."
                )
            else:
                self.env["ozon.products.indicator.summary"].create(
                    {
                        "name": f"Продукт имеет менее 3х конкурентов в течение дней: {days}. "
                                f"Цена не может быть рассчитана. Добавьте товары конкурентов.",
                        "type": "no_competitor_robot",
                        "ozon_product_id": record.id,
                    }
                )
        elif indicator_no_competitor_r and indicator_no_competitor_m:
            manager = indicator_no_competitor_m.user_id
            expiration_date = indicator_no_competitor_m.expiration_date.strftime(
                "%d.%m.%Y"
            )
            create_date = indicator_no_competitor_m.create_date.strftime("%d.%m.%Y")
            summary_m = summary_types.get("no_competitor_manager")
            if summary_m:
                summary_m.name = (
                    f"{manager.name} {create_date} подтвердил, что у продукта менее 3х "
                    f"товаров- конкурентов. Цена может быть рассчитана без их учета, "
                    f"что снизит точность прогнозирования правильной ценовой стратегии. "
                    f"Этот индикатор будет действовать до {expiration_date}"
                )
            else:
                self.env["ozon.products.indicator.summary"].create(
                    {
                        "name": f"{manager.name} {create_date} подтвердил, что у продукта менее 3х "
                                f"товаров- конкурентов. Цена может быть рассчитана без их учета, "
                                f"что снизит точность прогнозирования правильной ценовой стратегии. "
                                f"Этот индикатор будет действовать до {expiration_date}",
                        "type": "no_competitor_manager",
                        "ozon_product_id": record.id,
                    }
                )

            # delete robot's summary
            summary_r = summary_types.get("no_competitor_robot")
            if summary_r:
                record.ozon_products_indicators_summary_ids = [(2, summary_r.id, 0)]

        elif not indicator_no_competitor_r:
            summary_r = summary_types.get("no_competitor_robot")
            summary_m = summary_types.get("no_competitor_manager")
            for summary in (summary_r, summary_m):
                if summary:
                    record.ozon_products_indicators_summary_ids = [
                        (2, summary.id, 0)
                    ]

    def _update_in_out_indicator_summary(self, record, indicator_types=None, summary_types=None):
        if not indicator_types:
            indicator_types, summary_types = self._get_indicators_and_summaries_types(record)

        in_stock_indicator = indicator_types.get("in_stock")
        out_of_stock_indicator = indicator_types.get("out_of_stock")
        in_stock_summary = summary_types.get("in_stock")
        out_of_stock_summary = summary_types.get("out_of_stock")
        if in_stock_indicator:
            days = (datetime.now() - in_stock_indicator.create_date).days
            if out_of_stock_summary:
                record.ozon_products_indicators_summary_ids = [
                    (2, out_of_stock_summary.id, 0)
                ]
            if in_stock_summary:
                in_stock_summary.name = f"Товар в продаже дней: {days}."
            else:
                self.env["ozon.products.indicator.summary"].create(
                    {
                        "name": f"Товар в продаже дней: {days}.",
                        "type": "in_stock",
                        "ozon_product_id": record.id,
                    }
                )
        elif out_of_stock_indicator:
            days = (datetime.now() - out_of_stock_indicator.create_date).days
            lost_revenue_per_day = self._calculate_a_lost_revenue(
                record, out_of_stock_indicator.create_date
            )
            lost_revenue = round(lost_revenue_per_day * days, 2)

            if in_stock_summary:
                record.ozon_products_indicators_summary_ids = [
                    (2, in_stock_summary.id, 0)
                ]
            if out_of_stock_summary:
                out_of_stock_summary.name = (
                    f"Товар отсутствует дней: {days}. "
                    f"Упущенная выручка: {lost_revenue} руб."
                )
            else:
                self.env["ozon.products.indicator.summary"].create(
                    {
                        "name": f"Товар отсутствует дней: {days}. "
                        f"Упущенная выручка: {lost_revenue} руб.",
                        "type": "out_of_stock",
                        "ozon_product_id": record.id,
                    }
                )

    def _update_bcg_group_indicator_summary(self, record, indicator_types=None, summary_types=None):
        if not indicator_types:
            indicator_types, summary_types = self._get_indicators_and_summaries_types(record)

        bcg_indicator = indicator_types.get('bcg_group')
        bcg_summary = summary_types.get('bcg_group_expired')
        if bcg_indicator:
            if (
                    (datetime.now() - timedelta(days=10)).date() < bcg_indicator.write_date.date() <= (
                    datetime.now() - timedelta(days=5)).date()
            ):
                # tasks
                self.categories_to_tasks['bcg_reminder'][record.categories] = record.categories.name_categories

            if bcg_indicator.write_date.date() <= (datetime.now() - timedelta(days=10)).date():
                days = (datetime.now() - bcg_indicator.write_date).days
                if bcg_summary:
                    bcg_summary.name = (f"BCG группа не рассчитана дней: {days}. Рекомендации по продвижению "
                                        f"продукта могут быть не верны. Постройте BCG матрицу категории.")
                else:
                    self.env["ozon.products.indicator.summary"].create(
                        {
                            "name": f"BCG группа не рассчитана дней: {days}. Рекомендации по продвижению "
                                        f"продукта могут быть не верны. Постройте BCG матрицу категории.",
                            "type": "bcg_group_expired",
                            "ozon_product_id": record.id,
                        }
                    )
                # tasks
                self.categories_to_tasks['bcg_expired'][record.categories] = record.categories.name_categories
            else:
                if bcg_summary:
                    return bcg_summary.id
        else:
            if bcg_summary:
                return bcg_summary.id

    def _update_abc_group_indicator_summary(self, record, indicator_types=None, summary_types=None):
        if not indicator_types:
            indicator_types, summary_types = self._get_indicators_and_summaries_types(record)

        abc_indicator = indicator_types.get('abc_group')
        abc_summary = summary_types.get('abc_group_expired')
        if abc_indicator:
            if (
                    (datetime.now() - timedelta(days=10)).date() < abc_indicator.write_date.date() <= (
                    datetime.now() - timedelta(days=5)).date()
            ):
                # tasks
                self.categories_to_tasks['abc_reminder'][record.categories] = record.categories.name_categories

            if abc_indicator.write_date.date() <= (datetime.now() - timedelta(days=10)).date():
                days = (datetime.now() - abc_indicator.write_date).days
                if abc_summary:
                    abc_summary.name = (f"ABC группа не рассчитана дней: {days}. Информация о товаре "
                                        f"может быть неверна. Проведите ABC анализ категории.")
                else:
                    self.env["ozon.products.indicator.summary"].create(
                        {
                            "name": f"ABC группа не рассчитана дней: {days}. Информация о товаре "
                                    f"может быть неверна. Проведите ABC анализ категории.",
                            "type": "abc_group_expired",
                            "ozon_product_id": record.id,
                        }
                    )
                # tasks
                self.categories_to_tasks['abc_expired'][record.categories] = record.categories.name_categories
            else:
                if abc_summary:
                    return abc_summary.id
        else:
            if abc_summary:
                return abc_summary.id

    @api.depends("ozon_products_indicator_ids", "ozon_products_indicators_summary_ids")
    def _compute_ozon_products_indicator_qty(self):
        for record in self:
            need_actions = 0
            # calculate qty per type
            for summary in record.ozon_products_indicators_summary_ids:
                if summary.type in (
                    "no_competitor_robot",
                    "cost_not_calculated",
                    "out_of_stock",
                ):
                    need_actions += 1
            # set tags
            if need_actions:
                record.ozon_products_indicator_qty = need_actions
            else:
                record.ozon_products_indicator_qty = 0

    def _touch_bcg_group_indicator(self, record):
        bcg_group_indicator = None
        for indicator in record.ozon_products_indicator_ids:
            if indicator.type == "bcg_group":
                if record.bcg_group != indicator.value:
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
                else:
                    indicator.write_date = datetime.now()
        if not bcg_group_indicator and record.bcg_group != 'e':
            self.env["ozon.products.indicator"].create(
                {
                    "ozon_product_id": record.id,
                    "source": "robot",
                    "type": "bcg_group",
                    "value": record.bcg_group,
                }
            )

    def _touch_abc_group_indicator(self, record):
        abc_group_indicator = None
        for indicator in record.ozon_products_indicator_ids:
            if indicator.type == "abc_group":
                if record.abc_group != indicator.value:
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
                else:
                    indicator.write_date = datetime.now()
        if not abc_group_indicator and record.abc_group:
            self.env["ozon.products.indicator"].create(
                {
                    "ozon_product_id": record.id,
                    "source": "robot",
                    "type": "abc_group",
                    "value": record.abc_group,
                }
            )

    def _check_investment_expenses(self, record, summary_update=True):
        if not record.investment_expenses_id:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_investment_expenses":
                    found = 1
                    break
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "no_investment_expenses",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )
        else:
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_investment_expenses":
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
        # обновить выводы по индикаторам
        if summary_update:
            self._update_cost_price_investment_profitability_norm_indicators_summary(record)

    def _check_profitability_norm(self, record, summary_update=True):
        if not record.profitability_norm:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_profitability_norm":
                    found = 1
                    break
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "no_profitability_norm",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )
        else:
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_profitability_norm":
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
        # обновить выводы по индикаторам
        if summary_update:
            self._update_cost_price_investment_profitability_norm_indicators_summary(record)

    def _check_cost_price(self, record, summary_update=True):
        cost_price = 0
        if record.fix_expenses:
            cost_price_record = [
                x for x in record.fix_expenses if x.name == "Себестоимость товара"
            ]
            if len(cost_price_record) == 1:
                cost_price = cost_price_record[0].price
        if cost_price == 0:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "cost_not_calculated":
                    found = 1
                    break
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "cost_not_calculated",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )
        else:
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "cost_not_calculated":
                    indicator.end_date = datetime.now().date()
                    indicator.active = False

        # обновить выводы по индикаторам
        if summary_update:
            self._update_cost_price_investment_profitability_norm_indicators_summary(record)

    def _check_competitors_with_price_ids_qty(self, record, summary_update=True):
        if len(record.competitors_with_price_ids) >= 3:
            for indicator in record.ozon_products_indicator_ids:
                if (
                    indicator.type == "no_competitor_manager"
                    or indicator.type == "no_competitor_robot"
                ):
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
        elif len(record.competitors_with_price_ids) < 3:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_competitor_robot":
                    found = 1
                    break
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "no_competitor_robot",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )
        # обновить выводы по индикаторам
        if summary_update:
            self._update_less_3_competitors_indicator_summary(record)

    def _not_enough_competitors_write(self, record):
        if (
                record.not_enough_competitors
                and not record.commentary_not_enough_competitors
        ):
            raise UserError("Напишите комментарий")
        for indicator in record.ozon_products_indicator_ids:
            if indicator.type == "no_competitor_manager":
                indicator.end_date = datetime.now().date()
                indicator.active = False

        user_id = self.env.uid
        exp_date = datetime.now() + timedelta(days=30)
        self.env["ozon.products.indicator"].create(
            {
                "ozon_product_id": record.id,
                "source": "manager",
                "type": "no_competitor_manager",
                "expiration_date": exp_date.date(),
                "user_id": user_id if user_id else False,
            }
        )
        # обновить выводы по индикаторам
        self._update_less_3_competitors_indicator_summary(record)

    def _update_in_out_stock_indicators(self, record, summary_update=True):
        if record.is_selling:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "out_of_stock":
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
                if indicator.type == "in_stock":
                    found = 1
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "in_stock",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )
        else:
            found = 0
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "in_stock":
                    indicator.end_date = datetime.now().date()
                    indicator.active = False
                if indicator.type == "out_of_stock":
                    found = 1
            if not found:
                self.env["ozon.products.indicator"].create(
                    {
                        "ozon_product_id": record.id,
                        "source": "robot",
                        "type": "out_of_stock",
                        "expiration_date": False,
                        "user_id": False,
                    }
                )
        # обновить выводы по индикаторам
        if summary_update:
            self._update_in_out_indicator_summary(record)

    def _calculate_a_lost_revenue(self, record, period_to: datetime.date) -> float:
        avg_revenue_per_day = 0
        period_from = period_to - timedelta(days=60)
        sales_last_3_month = self.env["ozon.sale"].search(
            [
                ("product", "=", record.id),
                ("date", ">", period_from),
                ("date", "<", period_to),
            ]
        )
        total_revenue = sum(sale.revenue for sale in sales_last_3_month)
        if total_revenue:
            avg_revenue_per_day = total_revenue / 60

        return avg_revenue_per_day

    # cron
    def _automated_daily_action_by_cron_check_indicators_time(self):
        products = self.env["ozon.products"].search([])
        ids_to_delete = []
        for record in products:
            # проверяет не устарел ли индикатор no_competitor_manager и архивирует если да
            for indicator in record.ozon_products_indicator_ids:
                if indicator.type == "no_competitor_manager":
                    if indicator.expiration_date <= datetime.now().date():
                        indicator.end_date = datetime.now().date()
                        indicator.active = False

            summary_id = self._update_bcg_group_indicator_summary(record)
            if summary_id:
                ids_to_delete.append(summary_id)
            summary_id = self._update_abc_group_indicator_summary(record)
            if summary_id:
                ids_to_delete.append(summary_id)

        query = """
                    DELETE FROM ozon_products_indicator_summary
                    WHERE id IN %s
                """
        if ids_to_delete:
            self.env.cr.execute(query, (tuple(ids_to_delete),))
            logger.warning(f"delete from ozon_products_indicator_summary id in {ids_to_delete}")

        # tasks
        self._crud_ozon_report_task()

    def _crud_ozon_report_task(self):
        ozon_report_tasks_ids = set(self.env["ozon.report.task"].search([]).ids)
        sequences = {
            'abc_reminder': 3,
            'abc_expired': 1,
            'bcg_reminder': 3,
            'bcg_expired': 1,
        }
        for type_, dict_ in self.categories_to_tasks.items():
            for category, cat_name in dict_.items():
                texts = {
                    'abc_reminder': f"Не забудьте провести ABC анализ категории {cat_name}",
                    'abc_expired': f"Срочно проведите ABC анализ категории {cat_name} за новый период. "
                                   f"Время проведения просрочено!",
                    'bcg_reminder': f"Не забудьте загрузить данные о продажах конкурентов "
                                    f"категории {cat_name} "
                                    f"за новый период, рассчитать долю рынка и создать BCG матрицу.",
                    'bcg_expired': f"Срочно загрузите данные о продажах конкурентов "
                                   f"категории {cat_name} "
                                   f"за новый период, рассчитайте долю рынка и создайте BCG матрицу. "
                                   f"Время проведения просрочено!",
                }
                text = texts.get(type_) if texts.get(type_) else ''
                sqc = sequences.get(type_) if sequences.get(type_) else 3

                task = self.env["ozon.report.task"].search([
                    ('type', '=', type_),
                    ('ozon_categories_id', '=', category.id),
                ])
                if task and task.id in ozon_report_tasks_ids:
                    ozon_report_tasks_ids.remove(task.id)
                if not task:
                    self.env["ozon.report.task"].create({
                        'type': type_,
                        'ozon_categories_id': category.id,
                        'task': text,
                        'sequence': sqc,
                    })

        # deactivate remaining tasks
        tasks_to_deactivate = self.env["ozon.report.task"].browse(
            ozon_report_tasks_ids
        )
        for task in tasks_to_deactivate:
            task.active = False

    # cron
    def _automated_daily_action_by_cron_manager_report(self):
        # tasks
        tasks = self.env["ozon.report.task"].search([])
        tasks_per_user = defaultdict(list)
        for task in tasks:
            tasks_per_user[task.ozon_categories_id.category_manager.id].append(task.id)

        types_for_report = [
            "no_competitor_robot",
            "cost_not_calculated",
            "out_of_stock",
            "bcg_group_expired",
            "abc_group_expired",
        ]
        products = self.env["ozon.products"].search([])
        lots_with_indicators = defaultdict(list)
        for record in products:

            summary_types = defaultdict()
            for summary in record.ozon_products_indicators_summary_ids:
                summary_types[summary.type] = summary

            for type_ in summary_types:
                if type_ in types_for_report:
                    lots_with_indicators[record.categories.category_manager.id].append(
                        record.id
                    )
                    break

        self._create_manager_indicator_report(lots_with_indicators, tasks_per_user)

    def _create_manager_indicator_report(self, lots_with_indicators, tasks_per_user):
        # deactivate old reports
        reports = self.env["ozon.report"].search([("type", "=", "indicators")])
        for report in reports:
            report.active = False
        for manager_id, lots_ids in lots_with_indicators.items():
            if manager_id:
                task_ids = []
                if tasks_per_user.get(manager_id):
                    task_ids = tasks_per_user.pop(manager_id)
                self.env["ozon.report"].create(
                    {
                        "type": "indicators",
                        "res_users_id": manager_id,
                        "ozon_products_ids": lots_ids,
                        "lots_quantity": len(lots_ids),
                        "ozon_report_task_ids": task_ids,
                    }
                )

        # create reports with remaining tasks
        for manager_id, task_ids in tasks_per_user.items():
            if manager_id:
                self.env["ozon.report"].create(
                    {
                        "type": "indicators",
                        "res_users_id": manager_id,
                        "ozon_report_task_ids": task_ids,
                    }
                )

    @api.depends("stocks_fbs", "stocks_fbo")
    def _get_is_selling(self):
        for record in self:
            curr_val = copy(record.is_selling)
            if record.stocks_fbs > 0 or record.stocks_fbo > 0:
                record.is_selling = True
            else:
                record.is_selling = False
            if curr_val != record.is_selling:
                self._update_in_out_stock_indicators(record)

    def _compute_is_alive(self):
        for record in self:
            cost_price = self.env["retail.cost_price"].search(
                [("product_id", "=", record.products.id)]
            )
            if cost_price and (
                record.is_selling or record.sales_per_day_last_30_days > 0
            ):
                record.is_alive = True
            else:
                record.is_alive = False

    def update_coefs_and_groups(self):
        all_products = self.search([])
        for i, prod in enumerate(all_products):
            # coefs
            prod._compute_coef_profitability()
            prod._compute_sales_per_day_last_30_days()
            # product calculator ids
            prod._compute_product_calculator_ids()
            # is_alive
            prod._compute_is_alive()
            print(
                f"{i} - Product {prod.id_on_platform} calculator_ids, coef_profitability, sales_per_day_last_30_days and is_alive were updated"
            )
        # groups
        alive_products = self.search([("is_alive", "=", True)])
        not_alive_products = all_products - alive_products
        for i, rec in enumerate(not_alive_products):
            rec.coef_profitability_group = ""
            rec.sales_per_day_last_30_days_group = ""
            print(f"{i} - Not alive product {rec.id_on_platform} was updated")
        alive_products._compute_coef_profitability_group()
        alive_products._compute_sales_per_day_last_30_days_group()

    def update_percent_expenses(self):
        latest_indirect_expenses = self.env["ozon.indirect_percent_expenses"].search(
            [],
            limit=1,
            order="create_date desc",
        )
        coef_total = latest_indirect_expenses.coef_total / 100
        coef_total_percentage_string = f"{coef_total:.2%}"

        all_products = self.env["ozon.products"].search([])
        for i, product in enumerate(all_products):
            if coef_total_record := product.percent_expenses.filtered(
                lambda r: r.name == "Общий коэффициент косвенных затрат"
            ):
                coef_total_record.write(
                    {
                        "price": round(product.price * coef_total, 2),
                        "discription": coef_total_percentage_string,
                    }
                )
            else:
                self.env["ozon.cost"].create(
                    {
                        "name": "Общий коэффициент косвенных затрат",
                        "price": round(product.price * coef_total, 2),
                        "discription": coef_total_percentage_string,
                        "product_id": product.id,
                    }
                )
            print(
                f"{i} - Product {product.id_on_platform} percent expenses were updated."
            )

    def update_all_expenses(self):
        latest_indirect_expenses = self.env["ozon.indirect_percent_expenses"].search(
            [], limit=1, order="id desc"
        )
        all_products = self.env["ozon.products"].search([])
        self.env["ozon.all_expenses"].create_update_all_product_expenses(
            all_products, latest_indirect_expenses
        )

    def update_current_product_all_expenses(self, expected_price):
        self.ensure_one()
        latest_indirect_expenses = self.env["ozon.indirect_percent_expenses"].search(
            [], limit=1, order="id desc"
        )
        if not latest_indirect_expenses:
            raise UserError("Невозможно рассчитать. Отсутствует отчёт о выплатах.")
        self.env["ozon.all_expenses"].create_update_all_product_expenses(
            self, latest_indirect_expenses, expected_price
        )

    def get_view(self, view_id=None, view_type="form", **options):
        res = super(Product, self).get_view(view_id=view_id, view_type=view_type)
        if view_type == "form":
            # view = self.env["ir.ui.view"].search([("id", "=", res["id"])], limit=1)
            doc = etree.XML(res["arch"])
            af = "autofocus"
            params = self.env.context.get("params")
            if params:
                prod_id = params.get("id")
                if prod_id:
                    prod = self.browse(prod_id)
                    if prod.trading_scheme == "FBS":
                        doc.xpath('//page[@id="page_fbs_fix"]')[0].set(af, af)
                        doc.xpath('//page[@id="page_fbs_percent"]')[0].set(af, af)

                    elif prod.trading_scheme == "FBO":
                        doc.xpath('//page[@id="page_fbo_fix"]')[0].set(af, af)
                        doc.xpath('//page[@id="page_fbo_percent"]')[0].set(af, af)

            res["arch"] = etree.tostring(doc, encoding="unicode")

        return res

    def create_mass_pricing_without_dialog(self):
        self.ensure_one()
        competitor_pricing_strategy = self.calculated_pricing_strategy_ids.filtered(
            lambda r: r.pricing_strategy_id.strategy_id == "lower_min_competitor")
        competitor_pricing_strategy.ensure_one()
        # new_price = self.product_calculator_ids.filtered(
        #     lambda r: r.name == "Ожидаемая цена по всем стратегиям"
        # ).new_value
        new_price = competitor_pricing_strategy.expected_price
        self.env["ozon.mass_pricing"].create(
            {"product": self.id, "price": self.price, "new_price": new_price}, product=self)

    def _compute_imgs(self):
        for rec in self:
            rec.imgs_html = False
            if rec.imgs_urls:
                render_html = []
                imgs_urls_list = ast.literal_eval(rec.imgs_urls)
                for img in imgs_urls_list:
                    render_html.append(f"<img src='{img}' width='400'/>")

                rec.imgs_html = "\n".join(render_html)

    def _compute_product_calculator_ids(self):
        for rec in self:
            if pc_recs := rec.product_calculator_ids:
                for pc_rec in pc_recs:
                    if pc_rec.name == "Ожидаемая цена по всем стратегиям":
                        pc_rec.value = rec.price
            else:
                self.env["ozon.product_calculator"].create(
                    [
                        {
                            "name": "Ожидаемая цена по всем стратегиям",
                            "product_id": rec.id,
                            "value": rec.price,
                        }
                    ]
                )

    def get_minimal_competitor_price(self):
        comp_prices = self.competitors_with_price_ids.mapped("price")
        return min(comp_prices) if comp_prices else 0

    @api.onchange("calculated_pricing_strategy_ids")
    def calculate_calculated_pricing_strategy_ids(self):
        if not self.calculated_pricing_strategy_ids.pricing_strategy_id:
            return
        self._compute_product_calculator_ids()
        prices = []
        errors = False
        for price_strategy in self.calculated_pricing_strategy_ids:
            strategy_value = price_strategy.value
            strategy_id = price_strategy.pricing_strategy_id.strategy_id

            if strategy_id == "lower_min_competitor":
                if ind_sum := self.ozon_products_indicators_summary_ids.filtered(
                    lambda r: r.type.startswith("no_competitor")
                ):
                    price_strategy.message = (
                        "Невозможно рассчитать цену. У товара меньше 3ёх конкурентов"
                    )
                    errors = True
                else:
                    comp_prices = self.competitors_with_price_ids.mapped("price")
                    min_comp_price = min(comp_prices)
                    new_price = round(min_comp_price * (1 - strategy_value), 2)

            if strategy_id == "expected_price":
                if not self.retail_product_total_cost_price:
                    errors = True
                    price_strategy.message = (
                        "Невозможно рассчитать цену. Не задана себестоимость"
                    )
                # TODO: переделать, когда появятся соотв. индикаторы
                if not self.profitability_norm:
                    errors = True
                    price_strategy.message = (
                        "Невозможно рассчитать цену. Не задана ожидаемая доходность"
                    )

                if not self.investment_expenses_id:
                    errors = True
                    price_strategy.message = (
                        "Невозможно рассчитать цену. Не задан Investment"
                    )
                new_price = self.expected_price

            self.calculated_pricing_strategy_ids.timestamp = fields.Date.today()
            if errors:
                self.product_calculator_ids.new_value = 0
                return
            else:
                price_strategy.expected_price = new_price
                price_strategy.message = str(round(new_price, 2))

            prices.append(round(new_price * price_strategy.weight))

        for prod_calc_rec in self.product_calculator_ids:
            if prod_calc_rec.name == "Ожидаемая цена по всем стратегиям":
                prod_calc_rec.new_value = mean(prices)


    def _compute_calculator_delta(self):
        for r in self:
            r.calculator_delta = (r.expected_price 
                                  - sum(r.all_expenses_except_roi_roe_ids.mapped("expected_value")))
    
    def _price_comparison(self, identifier):
        return self.price_comparison_ids.filtered(
            lambda r: r.price_component_id.identifier == identifier)

    def _base_calculation(self, identifier):
        return self.base_calculation_ids.filtered(
            lambda r: r.price_component_id.identifier == identifier)

    def calculate_price_comparison_ids_plan_column(self):
        pc_model = self.env["ozon.price_comparison"]
        for r in self:
            suffix = f"для товара (Арт:{r.article})"
            pc_model.fill_with_blanks_if_not_exist(r)
            if not r.base_calculation_template_id:
                raise UserError(f"Шаблон планового расчёта не задан " + suffix)
            r.base_calculation_template_id.apply_to_products(r)
            pc_model.update_plan_column_for_product(r)
            r.plan_calc_date = fields.Date.today()
            print(f"«План» обновлён " + suffix)
    
    def calculate_price_comparison_ids_fact_column(self):
        pc_model = self.env["ozon.price_comparison"]
        for r in self:
            pc_model.fill_with_blanks_if_not_exist(r)
            r.update_current_product_all_expenses(r.price)
            pc_model.update_fact_column_for_product(r)
            r.fact_calc_date = fields.Date.today()
            print(f"«Факт» обновлён для товара (Арт:{r.article})")

    def calculate_price_comparison_ids_market_column(self):
        pc_model = self.env["ozon.price_comparison"]
        for r in self:
            pc_model.fill_with_blanks_if_not_exist(r)
            pc_model.update_market_column_for_product(r)
            print(f"«Рынок» обновлён для товара (Арт:{r.article})")

    def calculate_price_comparison_ids_calc_column(self):
        pc_model = self.env["ozon.price_comparison"]
        for r in self:
            pc_model.fill_with_blanks_if_not_exist(r)
            pc_model.update_calc_column_for_product(r)

    def reset_base_calculation_ids(self):
        self.env["ozon.base_calculation"].reset_for_products(self)
        self.env["ozon.price_comparison"].update_for_products(self)

    @api.depends("posting_ids")
    def _compute_count_postings(self):
        for record in self:
            record.postings_count = len(record.posting_ids)

    def get_postings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "История продаж",
            "view_mode": "tree",
            "res_model": "ozon.posting",
            "domain": [
                ("product_ids", "in", [self.id]),
            ],
            "context": {"create": False},
        }

    def _compute_supply_orders_count(self):
        for record in self:
            record.supply_orders_count = len(record.fbo_supply_order_product_ids)

    def get_supply_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Поставки",
            "view_mode": "tree,form",
            "res_model": "ozon.fbo_supply_order_product",
            "domain": [
                ("product_id", "=", [self.id]),
            ],
            "context": {"create": False},
        }

    def _compute_stock_history_count(self):
        for rec in self:
            rec.stock_history_count = len(rec.stock_ids)

    def get_stocks(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "История остатков",
            "view_mode": "tree,form",
            # "res_id": self.id,
            "res_model": "ozon.stock",
            "domain": [
                ("product", "=", [self.id]),
            ],
            "context": {"create": False},
        }

    def _compute_is_button_create_mass_pricing_shown(self):
        for rec in self:
            if rec.calculated_pricing_strategy_ids.filtered(
                lambda r: r.pricing_strategy_id.strategy_id == "lower_min_competitor"):
                rec.is_button_create_mass_pricing_shown = True
            else:
                rec.is_button_create_mass_pricing_shown = False

    def action_run_indicators_checks(self):
        schedules = self.env["ozon.schedule"].search([])
        if not schedules:
            schedules = self.env["ozon.schedule"].create(
                {
                    "ozon_products_checking_last_time": datetime.now()
                    - timedelta(minutes=5)
                }
            )
        if (
            schedules[0].ozon_products_checking_last_time + timedelta(minutes=5)
            > datetime.now()
        ):
            return True

        products = self.env["ozon.products"].search([])
        for product in products:
            try:
                product._check_investment_expenses(product, summary_update=False)
                product._check_profitability_norm(product, summary_update=False)
                product._check_cost_price(product, summary_update=False)
                product._check_competitors_with_price_ids_qty(product, summary_update=False)
                product._update_in_out_stock_indicators(product, summary_update=False)

                product.update_indicator_summary(product)
                product.bcg_group = 'e'
            except:
                logger.warning('action_run_indicators_checks exception')

        schedules[0].ozon_products_checking_last_time = datetime.now()

    def open_base_calculation_wizard(self):
        self.env["ozon.base_calculation_template"].create_if_not_exists()
        bc_wiz_model = self.env["ozon.base_calculation_wizard"]
        bc_wiz_model.unlink()
        return {
            "type": "ir.actions.act_window", 
            "view_mode": "form", 
            "res_model": "ozon.base_calculation_wizard",
            "target": "new",
            }
    
    def get_products_by_cat_with_sales_for_period(self, data):
        date_from = data.get("date_from")
        date_to = data.get("date_to")
        cat_id = data.get("category_id")
        if date_from and date_to and cat_id:
            sales = self.env["ozon.transaction"].search([
                ("name", "=", "Доставка покупателю"),
                ("transaction_date", ">=", fields.Date.to_date(date_from)),
                ("transaction_date", "<=", fields.Date.to_date(date_to))])
            return self.search([("categories", "=", cat_id), ("id", "in", sales.products.ids)])
        
    
    def _compute_marketing_discount(self):
        for r in self:
            r.marketing_discount = (r.price - r.marketing_price) / r.price

class ProductNameGetExtension(models.Model):
    _inherit = "ozon.products"

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, f"{record.article}, {record.products.name}"))
        return result


class ProductQuikSearchExtension(models.Model):
    _inherit = "ozon.products"

    @api.model
    def _name_search(
        self, name="", args=None, operator="ilike", limit=10, name_get_uid=None
    ):
        args = list(args or [])
        if name:
            args += ["|", ("article", operator, name), ("products", operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)


class ProductKanbanExtension(models.Model):
    _inherit = "ozon.products"

    img_html = fields.Html(compute="_compute_img")

    def _compute_img(self):
        for rec in self:
            rec.img_html = False
            if rec.imgs_urls:
                render_html = []
                imgs_urls_list = ast.literal_eval(rec.imgs_urls)
                for img in imgs_urls_list:
                    render_html.append(f"<img src='{img}' width='150'/>")
                    break

                rec.img_html = "\n".join(render_html)


class ProductGraphExtension(models.Model):
    _inherit = "ozon.products"

    def action_draw_graphs(self):
        self.draw_sale()
        self.draw_sale_per_weeks()
        self.draw_price_history()
        self.draw_stock()
        self.draw_analysis_data()

    ### История цен (модель: ozon.price_history)
    img_data_price_history = fields.Text(string="Данные графика")
    img_price_history = fields.Binary()

    def draw_price_history(self):
        model_price_history = self.env["ozon.price_history"]
        year = self._get_year()

        for rec in self:
            payload = {
                "model": "price_history",
                "product_id": rec.id,
            }

            records = model_price_history.search(
                [
                    ("product", "=", rec.id),
                    ("timestamp", ">=", f"{year}-01-01"),
                    ("timestamp", "<=", f"{year}-12-31"),
                ]
            )
            graph_data = {"dates": [], "num": []}
            for record in records:
                graph_data["dates"].append(record.timestamp.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.price)
            payload["current"] = graph_data

            # rec.img_data_price_history = graph_data

            bytes_plot, data_current = df().post(payload)
            rec.img_price_history = bytes_plot
            rec.img_data_price_history = data_current

    ### История продаж по неделям (модель: ozon.sale)
    img_data_sale_two_weeks = fields.Text(string="Данные графика")
    img_sale_two_weeks = fields.Binary()

    def download_img_data_sale_two_weeks(self):
        field_name = "img_data_sale_two_weeks"
        url = self.get_download_url(field_name)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    img_data_sale_six_weeks = fields.Text(string="Данные графика")
    img_sale_six_weeks = fields.Binary()

    def download_img_data_sale_six_weeks(self):
        field_name = "img_data_sale_six_weeks"
        url = self.get_download_url(field_name)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    img_data_sale_twelve_weeks = fields.Text(string="Данные графика")
    img_sale_twelve_weeks = fields.Binary()

    def download_img_data_sale_twelve_weeks(self):
        field_name = "img_data_sale_twelve_weeks"
        url = self.get_download_url(field_name)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def draw_sale_per_weeks(self):
        model_sale = self.env["ozon.sale"]

        current_date = datetime.now()
        two_week_ago = current_date - timedelta(weeks=2)
        six_week_ago = current_date - timedelta(weeks=6)
        twelve_week_ago = current_date - timedelta(weeks=12)

        for rec in self:
            payload = {
                "model": "sale_by_week",
                "product_id": rec.id,
            }

            records = model_sale.search(
                [
                    ("product", "=", rec.id),
                    ("date", ">=", two_week_ago.strftime("%Y-%m-%d")),
                    ("date", "<=", current_date.strftime("%Y-%m-%d")),
                ]
            )
            graph_data = {"dates": [], "num": []}
            for record in records:
                graph_data["dates"].append(record.date.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.qty)
            payload["two_weeks"] = graph_data

            records = model_sale.search(
                [
                    ("product", "=", rec.id),
                    ("date", ">=", six_week_ago.strftime("%Y-%m-%d")),
                    ("date", "<=", current_date.strftime("%Y-%m-%d")),
                ]
            )
            graph_data = {"dates": [], "num": []}
            for record in records:
                graph_data["dates"].append(record.date.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.qty)
            payload["six_week"] = graph_data

            records = model_sale.search(
                [
                    ("product", "=", rec.id),
                    ("date", ">=", twelve_week_ago.strftime("%Y-%m-%d")),
                    ("date", "<=", current_date.strftime("%Y-%m-%d")),
                ]
            )
            graph_data = {"dates": [], "num": []}
            for record in records:
                graph_data["dates"].append(record.date.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.qty)
            payload["twelve_week"] = graph_data

            (
                two_week_bytes_plot, six_week_bytes_plot, twelve_week_bytes_plot,
                data_two_weeks, data_six_week, data_twelve_week
            ) = df().post(payload)
            rec.img_sale_two_weeks = two_week_bytes_plot
            rec.img_data_sale_two_weeks = data_two_weeks

            rec.img_sale_six_weeks = six_week_bytes_plot
            rec.img_data_sale_six_weeks = data_six_week

            rec.img_sale_twelve_weeks = twelve_week_bytes_plot
            rec.img_data_sale_twelve_weeks = data_twelve_week


    ### История продаж (модель: ozon.sale)
    img_data_sale_this_year = fields.Text(string="Данные графика")
    img_sale_this_year = fields.Binary()

    def download_img_data_sale_this_year(self):
        field_name = "img_data_sale_this_year"
        url = self.get_download_url(field_name)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }


    img_data_sale_last_year = fields.Text(string="Данные графика")
    img_sale_last_year = fields.Binary()

    def download_img_data_sale_last_year(self):
        field_name = "img_data_sale_last_year"
        url = self.get_download_url(field_name)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def draw_sale(self):
        model_sale = self.env["ozon.sale"]
        year = datetime.now().year
        last_year = year - 1

        for rec in self:
            payload = {
                "model": "sale",
                "product_id": rec.id,
            }

            records = model_sale.search(
                [
                    ("product", "=", rec.id),
                    ("date", ">=", f"{year}-01-01"),
                    ("date", "<=", f"{year}-12-31"),
                ]
            )

            graph_data = {"dates": [], "values": []}
            for record in records:
                graph_data["dates"].append(record.date.strftime("%Y-%m-%d"))
                graph_data["values"].append(record.qty)
            payload["current"] = graph_data

            if rec.categories.img_data_sale_this_year:
                payload["average_graph_this_year"] = (
                    rec.categories.img_data_sale_this_year
                )

            records = model_sale.search(
                [
                    ("product", "=", rec.id),
                    ("date", ">=", f"{last_year}-01-01"),
                    ("date", "<=", f"{last_year}-12-31"),
                ]
            )

            graph_data = {"dates": [], "values": []}
            for record in records:
                graph_data["dates"].append(record.date.strftime("%Y-%m-%d"))
                graph_data["values"].append(record.qty)
            payload["last"] = graph_data

            if rec.categories.img_data_sale_last_year:
                payload["average_graph_last_year"] = (
                    rec.categories.img_data_sale_last_year
                )

            res = df().post(payload)
            current_bytes_plot, last_bytes_plot, data_graph_current, data_graph_last = res
            rec.img_sale_this_year = current_bytes_plot
            rec.img_sale_last_year = last_bytes_plot
            rec.img_data_sale_this_year = data_graph_current
            rec.img_data_sale_last_year = data_graph_last

    ### История остатков (модель: ozon.stock)
    img_data_stock = fields.Text(string="Данные графика")
    img_stock = fields.Binary()

    def download_img_data_stock(self):
        field_name = "img_data_stock"
        url = self.get_download_url(field_name)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def draw_stock(self):
        model_stock = self.env["ozon.stock"]
        year = datetime.now().year

        for rec in self:
            payload = {
                "model": "stock",
                "product_id": rec.id,
            }

            records = model_stock.search(
                [
                    ("product", "=", rec.id),
                    ("timestamp", ">=", f"{year}-01-01"),
                    ("timestamp", "<=", f"{year}-12-31"),
                ]
            )

            graph_data = {"dates": [], "num": []}
            for record in records:
                graph_data["dates"].append(record.timestamp.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.stocks_fbs)
            payload["current"] = graph_data

            bytes_plot, data_current = df().post(payload)
            rec.img_stock = bytes_plot
            rec.img_data_stock = bytes_plot

    ### График интереса (модель: ozon.analysis_data)
    img_data_analysis_data = fields.Text(string="Данные графика")
    img_analysis_data = fields.Binary()

    def download_img_data_analysis_data(self):
        field_name = "img_data_analysis_data"
        url = self.get_download_url(field_name)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def draw_analysis_data(self):
        model_analysis_data = self.env["ozon.analysis_data"]
        year = self._get_year()

        for rec in self:
            records = model_analysis_data.search(
                [
                    ("product", "=", rec.id),
                    ("date", ">=", f"{year}-01-01"),
                    ("date", "<=", f"{year}-12-31"),
                ]
            )

            payload = {
                "model": "analysis_data",
                "product_id": rec.id,
                "hits_view": None,
                "hits_tocart": None,
                "average_data": None,
            }

            graph_data = {"dates": [], "num": []}
            for record in records:
                average_date = record.date

                graph_data["dates"].append(average_date.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.hits_view)
            payload["hits_view"] = graph_data

            graph_data = {"dates": [], "num": []}
            for record in records:
                average_date = record.date

                graph_data["dates"].append(average_date.strftime("%Y-%m-%d"))
                graph_data["num"].append(record.hits_tocart)
            payload["hits_tocart"] = graph_data

            if rec.categories.img_data_analysis_data_this_year:
                payload["average_data"] = (
                    rec.categories.img_data_analysis_data_this_year
                )

            bytes_plot, hits_view, hits_tocart = df().post(payload)
            rec.img_analysis_data = bytes_plot
            rec.img_data_analysis_data = {
                "hits_view": hits_view,
                "hits_tocart": hits_tocart,
            }

    def _get_year(self):
        return datetime.now().year

    def _get_records(self, model, record, year, timestamp_field):
        return model.search(
            [
                ("product", "=", record.id),
                (timestamp_field, ">=", f"{year}-01-01"),
                (timestamp_field, "<=", f"{year}-12-31"),
            ]
        )

    def action_open_lot_full_screen(self):
        return {
            "name": "Лот",
            "type": "ir.actions.act_window",
            "res_model": "ozon.products",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }


class GenerateUrlForDownloadGrpahData(models.Model):
    _inherit = "ozon.products"

    def get_url(self, model_name, record_id, field_name):
        return f"/web/content_text?model={model_name}&id={record_id}&field={field_name}"

    def get_download_url(self, field_name):
        model_name = self._name
        record_id = self.id
        url = self.get_url(model_name, record_id, field_name)
        return url

class ProductExpenses(models.Model):
    _inherit = "ozon.products"

    def get_expense_by_category(self, category):
        return self.all_expenses_ids.filtered(lambda r: r.category == category)
    
    @property
    def _logistics(self):
        return self.get_expense_by_category("Логистика")
    
    @property
    def _return_logistics(self):
        return self.get_expense_by_category("Обратная логистика")
    
    @property
    def _acquiring(self):
        return self.get_expense_by_category("Эквайринг")
    
    @property
    def _last_mile(self):
        return self.get_expense_by_category("Последняя миля")
    
    @property
    def _ozon_reward(self):
        return self.get_expense_by_category("Вознаграждение Ozon")
    
    @property
    def _processing(self):
        return self.get_expense_by_category("Обработка")
    
    @property
    def _promo(self):
        return self.get_expense_by_category("Реклама")
    
    @property
    def _tax(self):
        return self.get_expense_by_category("Налог")
    
class ProductTransactions(models.Model):
    _inherit = "ozon.products"

    def get_last_30_days_limits(self):
        date_from = (datetime.combine(datetime.now(), time.min) - timedelta(days=30)).date()
        date_to = (datetime.combine(datetime.now(), time.max) - timedelta(days=1)).date()
        return date_from, date_to
    
    @property
    def _last_30_days_sales(self):
        date_from, date_to = self.get_last_30_days_limits()
        return self.sales.filtered(lambda r: date_from <= r.date <= date_to)
    
    @property
    def _last_30_days_returns(self):
        date_from, date_to = self.get_last_30_days_limits()
        returns = (
            self.env["ozon.transaction"]
            .search([("name", "=", "Доставка и обработка возврата, отмены, невыкупа")])
            .filtered(lambda r: self in [r.products])
            .filtered(lambda r: date_from <= r.transaction_date <= date_to)
        )
        return returns

class ProductCalculator(models.Model):
    _name = "ozon.product_calculator"
    _description = "Калькулятор лота"

    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    name = fields.Char(string="Параметр", readonly=True)
    value = fields.Float(string="Текущее значение", readonly=True)
    new_value = fields.Float(string="Новое значение")

class ProductAllExpensesCalculation(models.Model):
    _inherit = "ozon.products"
    # input
    ozon_reward = fields.Float(string="Вознаграждение Озон (процент)")
    acquiring = fields.Float(string="Эквайринг (процент)")
    promo = fields.Float(string="Расходы на продвижение (процент)")
    return_logistics = fields.Float(string="Обратная логистика (процент)")
    # category
    ozon_reward_from_category = fields.Float(string="Вознаграждение Озон (процент)", 
                                             related="categories.ozon_reward")
    acquiring_from_category = fields.Float(string="Эквайринг (процент)", 
                                             related="categories.acquiring")
    promo_from_category = fields.Float(string="Расходы на продвижение (процент)", 
                                             related="categories.promo")
    return_logistics_from_category = fields.Float(string="Обратная логистика (процент)", 
                                             related="categories.return_logistics")
    # report
    ozon_reward_from_report = fields.Float(string="Вознаграждение Озон (процент)", 
                                           compute="_compute_from_indirect_percent_expenses_report")
    acquiring_from_report = fields.Float(string="Эквайринг (процент)", 
                                           compute="_compute_from_indirect_percent_expenses_report")
    promo_from_report = fields.Float(string="Расходы на продвижение (процент)", 
                                           compute="_compute_from_indirect_percent_expenses_report")
    return_logistics_from_report = fields.Float(string="Обратная логистика (процент)", 
                                           compute="_compute_from_indirect_percent_expenses_report")

    @property
    def _expenses_to_use_from_input(self):
        if self.avg_value_to_use == "input":
            return ["ozon_reward", "acquiring", "promo", "return_logistics"]
        else:
            return []
            

    def _compute_from_indirect_percent_expenses_report(self):
        report = self.env["ozon.indirect_percent_expenses"].get_latest()
        sums = report.transaction_unit_summary_ids
        for r in self:
            r.ozon_reward_from_report = abs(sums.filtered(
                lambda r: r.name == "Вознаграждение за продажу").percent)
            r.acquiring_from_report = abs(sums.filtered(
                lambda r: r.name == "Оплата эквайринга").percent)
            r.promo_from_report = abs(sums.filtered(
                lambda r: r.name == "Услуги продвижения товаров").percent)
            r.return_logistics_from_report = abs(sum(sums.filtered(lambda r: r.name in [
                "обратная логистика", 
                "MarketplaceServiceItemRedistributionReturnsPVZ"]).mapped("percent")))
    
    def open_avg_value_to_use_assign_form(self):
        return {
            "type": "ir.actions.act_window", 
            "view_mode": "form", 
            "res_model": "ozon.products.avg_value_to_use.assign",
            "target": "new",
            }