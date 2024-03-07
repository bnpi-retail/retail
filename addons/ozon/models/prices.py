# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from email.policy import default
from statistics import mean

from odoo import models, fields, api
from odoo.exceptions import UserError

from ..helpers import split_list_into_chunks_of_size_n
from .indirect_percent_expenses import (
    STRING_FIELDNAMES
)
from ..ozon_api import (
    MAX_FIX_EXPENSES_FBO,
    MAX_FIX_EXPENSES_FBS,
    FBO_PERCENT_COMMISSIONS,
    FBS_PERCENT_COMMISSIONS,
)


class FixExpenses(models.Model):
    _name = "ozon.fix_expenses"
    _description = "Фиксированные затраты"

    name = fields.Char(string="Наименование")
    price = fields.Float(string="Значение")
    discription = fields.Text(string="Описание")
    price_history_id = fields.Many2one("ozon.price_history", string="История цен")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")

    def create_from_ozon_product_fee(self, product_fee):
        data = []
        for k, v in product_fee._fields.items():
            if k in [
                "product",
                "sales_percent_fbo",
                "sales_percent_fbs",
                "sales_percent",
                "id",
                "__last_update",
                "display_name",
                "create_uid",
                "create_date",
                "write_uid",
                "write_date",
            ]:
                continue
            data.append(
                {
                    "name": v.string,
                    "price": product_fee[k],
                    "discription": "",
                }
            )
        recs = self.create(data)
        return recs


class Costs(models.Model):
    _name = "ozon.cost"
    _description = "Процент от продаж"

    name = fields.Char(string="Наименование")
    price = fields.Float(string="Значение")
    discription = fields.Text(string="Описание")
    price_history_id = fields.Many2one("ozon.price_history", string="История цен")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")

    def create_from_ozon_product_fee(self, product_fee, price):
        data = []
        for k, v in product_fee._fields.items():
            if k in ["sales_percent_fbo", "sales_percent_fbs"]:
                data.append(
                    {
                        "name": v.string,
                        "price": round(price * product_fee[k] / 100, 2),
                        "discription": f"{product_fee[k]}%",
                    }
                )
        recs = self.create(data)
        return recs


class PriceHistory(models.Model):
    _name = "ozon.price_history"
    _description = "История цен"

    product = fields.Many2one("ozon.products", string="Товар")
    id_on_platform = fields.Char(string="Product ID", readonly=True)
    provider = fields.Many2one("retail.seller", string="Продавец")
    price = fields.Float(string="Установленная цена", readonly=True)
    marketing_price = fields.Float(string="Установленная цена для покупателя", readonly=True)
    competitors = fields.One2many(
        "ozon.name_competitors",
        "pricing_history_id",
        string="Цены конкурентов",
        copy=True,
    )

    previous_price = fields.Float(string="Предыдущая цена", readonly=True)
    previous_marketing_price = fields.Float(string="Предыдущая цена для покупателя", readonly=True)
    timestamp = fields.Date(string="Дата", default=fields.Date.today, readonly=True)

    # @api.model
    def _change_fix_expenses_domain(self):
        for rec in self:
            if rec.product.trading_scheme == "FBS":
                domain = [("name", "in", MAX_FIX_EXPENSES_FBS)]
            elif rec.product.trading_scheme == "FBO":
                domain = [("name", "in", MAX_FIX_EXPENSES_FBO)]
            else:
                domain = []
            return domain

    fix_expenses = fields.One2many(
        "ozon.fix_expenses",
        "price_history_id",
        string="Фиксированные затраты максимальные",
        copy=True,
        readonly=True,
        domain=_change_fix_expenses_domain,
    )

    total_cost_fix = fields.Float(
        string="Итого фикс.затраты",
        compute="_compute_total_cost_fix",
        store=True,
    )

    @api.model
    def _change_costs_domain(self):
        indir_per_expenses = STRING_FIELDNAMES
        if indir_per_expenses.get("Выручка"):
            indir_per_expenses.pop("Выручка")
        for rec in self:
            if rec.product.trading_scheme == "FBS":
                domain = [
                    (
                        "name",
                        "in",
                        [
                            "Процент комиссии за продажу (FBS)",
                            *indir_per_expenses.keys(),
                        ],
                    )
                ]
            elif rec.product.trading_scheme == "FBO":
                domain = [
                    (
                        "name",
                        "in",
                        [
                            "Процент комиссии за продажу (FBO)",
                            *indir_per_expenses.keys(),
                        ],
                    )
                ]
            else:
                domain = []
            return domain

    costs = fields.One2many(
        "ozon.cost",
        "price_history_id",
        string="Процент от продаж",
        copy=True,
        readonly=True,
        domain=_change_costs_domain,
    )
    total_cost_percent = fields.Float(
        string="Итого проц.затраты",
        compute="_compute_total_cost_percent",
        store=True,
    )

    profit = fields.Float(
        string="Прибыль от установленной цены", compute="_compute_profit", store=True
    )
    profit_ideal = fields.Float(
        string="Идеальная прибыль", compute="_compute_profit_ideal", store=True
    )
    profit_delta = fields.Float(
        string="Разница между прибылью и идеальной прибылью",
        compute="_compute_profit_delta",
        store=True,
    )
    coef_profitability = fields.Float(
        string="Коэффициент прибыльности",
        compute="_compute_coef_profitability",
        store=True,
    )

    product_id = fields.Many2one("ozon.products", string="Лот")

    @api.depends("fix_expenses.price")
    def _compute_total_cost_fix(self):
        for record in self:
            record.total_cost_fix = sum(record.fix_expenses.mapped("price"))

    @api.depends("costs.price")
    def _compute_total_cost_percent(self):
        for record in self:
            record.total_cost_percent = sum(record.costs.mapped("price"))

    @api.depends("price", "total_cost_fix", "total_cost_percent")
    def _compute_profit(self):
        for record in self:
            record.profit = (
                record.price - record.total_cost_fix - record.total_cost_percent
            )

    @api.depends("price")
    def _compute_profit_ideal(self):
        for record in self:
            record.profit_ideal = record.price * 0.2

    @api.depends("profit", "profit_ideal")
    def _compute_profit_delta(self):
        for record in self:
            record.profit_delta = record.profit - record.profit_ideal

    @api.depends("profit", "profit_ideal")
    def _compute_coef_profitability(self):
        for record in self:
            record.coef_profitability = record.profit / record.profit_ideal

    @api.model
    def create(self, values):
        if values.get("fix_expenses"):
            ozon_product_id = values["product"]
            cost_price_record = self.env["ozon.fix_expenses"].search(
                [
                    ("product_id", "=", ozon_product_id),
                    ("name", "=", "Себестоимость товара"),
                ],
                order="create_date desc",
                limit=1,
            )
            values["fix_expenses"] = [cost_price_record.id] + values["fix_expenses"]

        record = super(PriceHistory, self).create(values)
        product = record.product
        product.write({"price_our_history_ids": [(4, record.id)]})
        return record

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            id = record.id
            result.append(
                (id, f"{record.timestamp},  " f"{record.product.products.name}")
            )
        return result


class ProfitabilityNorm(models.Model):
    _name = "ozon.profitability_norm"
    _description = "Ожидаемая доходность"

    name = fields.Char(string="Наименование")
    value = fields.Float(string="Значение")


class ProfitabilityNormWizard(models.TransientModel):
    _name = "ozon.profitability_norm.wizard"
    _description = "Wizard Ожидаемая доходность"

    profitability_norm = fields.Many2one(
        "ozon.profitability_norm", string="Ожидаемая доходность"
    )

    def change_profitability_norm(self):
        prod_ids = self._context["active_ids"]
        products = self.env["ozon.products"].browse(prod_ids)
        products.write({"profitability_norm": self.profitability_norm})


class InvestmentExpenses(models.Model):
    _name = "ozon.investment_expenses"
    _description = "Investment"

    name = fields.Char(string="Наименование")
    value = fields.Float(string="Значение")


class InvestmentExpensesWizard(models.TransientModel):
    _name = "ozon.investment_expenses.wizard"
    _description = "Wizard Инвестиционные затраты"

    investment_expenses_id = fields.Many2one(
        "ozon.investment_expenses", string="Investment"
    )

    def change_investment_expenses(self):
        prod_ids = self._context["active_ids"]
        products = self.env["ozon.products"].browse(prod_ids)
        products.write({"investment_expenses_id": self.investment_expenses_id})


ALL_EXPENSES_NAMES_IDENTIFIERS = {
    'Себестоимость товара': 1,
    'Услуги продвижения товаров': 2,
    'Получение возврата, отмены, невыкупа от покупателя': 3, 
    'Доставка и обработка возврата, отмены, невыкупа': 4, 
    'Обработка отправления «Pick-up» (отгрузка курьеру)': 5, 
    'Услуги доставки Партнерами Ozon на схеме realFBS': 6, 
    'Агентское вознаграждение за доставку Партнерами Ozon на схеме realFBS': 7, 
    'Услуга продвижения Бонусы продавца': 8, 
    'Приобретение отзывов на платформе': 9, 
    'Подписка Premium Plus': 10, 
    'Услуга за обработку операционных ошибок продавца: отмена': 11, 
    'Услуга за обработку операционных ошибок продавца: просроченная отгрузка': 12, 
    'Обработка товара в составе грузоместа на FBO': 13, 
    'Обработка сроков годности на FBO': 14, 
    'Утилизация': 15, 
    'Услуга по бронированию места и персонала для поставки с неполным составом': 16, 
    'Прочее': 17,
    'Процент комиссии за продажу (FBS)': 18,
    'Процент комиссии за продажу (FBO)': 19,
    'Процент комиссии за продажу (rFBS)': 20,
    'Последняя миля (FBO)': 21,
    'Магистраль до (FBO)': 22,
    'Комиссия за сборку заказа (FBO)': 23,
    'Последняя миля (FBS)': 24,
    'Магистраль до (FBS)': 25,
    'Максимальная комиссия за обработку отправления (FBS) — 25 рублей': 26,
    'Максимальная комиссия за эквайринг': 27,
    'Налог': 28,
    'Доходность': 29,
    'Investment': 30,
    'Обработка и хранение (компания)': 31,
    'Упаковка (компания)': 32,
    'Маркетинг (компания)': 33,
    'Операторы (компания)': 34
}

class AllExpenses(models.Model):
    _name = "ozon.all_expenses"
    _description = "Все затраты по товару Ozon"

    identifier = fields.Integer(string="Идентификатор", compute="_compute_identifier")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    name = fields.Char(string="Название")
    description = fields.Char(string="Описание")
    comment = fields.Text(string="Комментарий", readonly=True, compute="_compute_comment")
    kind = fields.Selection(
        [("fix", "Фиксированный"), ("percent", "Процентный")],
        string="Тип",
        readonly=True,
    )
    category = fields.Char(string="Категория затрат", readonly=True)
    percent = fields.Float(string="Процент")
    value = fields.Float(string="Абсолютное значение в руб, исходя из текущей цены")
    expected_value = fields.Float(string="Ожидаемое значение")

    def _compute_identifier(self):
        for r in self:
            r.identifier = ALL_EXPENSES_NAMES_IDENTIFIERS.get(r.name, 0)

    def _compute_comment(self):
        for r in self:
            r.comment = ""
        # exp = self.env["ozon.indirect_percent_expenses"].search(
        #     [],
        #     limit=1,
        #     order="create_date desc",
        # )
        # if not exp:
        #     raise UserError("Косвенные затраты не посчитаны. Невозможно рассчитать значения в калькуляторе")

        # period = (f"{datetime.strftime(exp.date_from, '%d %b %Y')}" 
        #           f" - {datetime.strftime(exp.date_to, '%d %b %Y')}")
        for r in self:
            name = r.name
            val = r.value
            exp_val = round(r.expected_value, 2)
            per = round(r.percent, 6)
            price = r.product_id.price
            exp_price = r.product_id.expected_price
            tax = r.product_id.seller.tax
            tax_percent = r.product_id.seller.tax_percent
            if name == "Себестоимость товара":
                if val == 0:
                    r.comment = "Себестоимость товара не указана"
                else:
                    r.comment = """Себестоимость из модуля "Розничная торговля" """
            elif name == "Налог":
                if not tax:
                    r.comment = f"{name} не задан у продавца."
                else:
                    r.comment = ("Цена * процент налогообложения = текущий налог\n"
                                f"{price} * {tax_percent} = {val}\n")
            else:
                r.comment = ("""Данные из "Отчёта о выплатах".\n"""
                             "Рассчитывается как цена, умноженная на процент фактической статьи затрат.\n"
                             "Цена * Фактическая статья(процент от выручки) = Значение\n"
                             f"{price} * {per} = {val}")

                
    def update_all_expenses(self, products, latest_indirect_expenses):
        for idx, prod in enumerate(products):
            exp_price = prod.expected_price
            if exp_price == 0:
                continue
            if all_expenses := prod.all_expenses_ids:
                all_exp_profit_norm = prod.all_expenses_only_roi_roe_ids.filtered(
                        lambda r: r.name == "Доходность"
                    )
                all_exp_invest = prod.all_expenses_only_roi_roe_ids.filtered(
                        lambda r: r.name == "Investment"
                    )
                delta = exp_price - sum(prod.all_expenses_except_roi_roe_ids.mapped("expected_value"))
                all_exp_profit_norm.percent = delta / exp_price
                all_exp_profit_norm.expected_value = all_exp_profit_norm.percent * exp_price
                all_exp_invest.percent = all_exp_profit_norm.percent / 2
                all_exp_invest.expected_value = all_exp_invest.percent * exp_price
 
            else:
                self.create_update_all_product_expenses(prod, latest_indirect_expenses, exp_price)
            print(f"{idx}th product all expenses were updated")

    def create_update_all_product_expenses(self, products, latest_indirect_expenses, expected_price=None):
        tran_sums = latest_indirect_expenses.transaction_unit_summary_ids.filtered(
            lambda r: r.percent < 0)
        fact_plan_match = self.env["ozon.price_component_match"].get_fact_plan_match()
        data = []
        for idx, prod in enumerate(products):
            tax_percent = prod.seller.tax_percent
            tax_description = prod.seller.tax_description
            total_expenses = 0
            price = prod.price
            if expected_price:
                exp_price = expected_price
            else:
                exp_price = prod.expected_price
            # себестоимость
            cost_price = prod.products.total_cost_price
            data.append(
                {
                    "product_id": prod.id,
                    "name": "Себестоимость товара",
                    "kind": "fix",
                    "category": "Себестоимость",
                    "percent": cost_price / price,
                    "value": cost_price,
                    "expected_value": cost_price,
                }
            )
            total_expenses += prod.products.total_cost_price
            # продвижение товара
            name = "Услуги продвижения товаров"
            # # если есть фактические данные по затратам на рекламу по данному товару
            # promo_expenses = prod.promotion_expenses_ids.filtered(
            #     lambda r: latest_indirect_expenses.date_from <= r.date <= latest_indirect_expenses.date_to)
            # if promo_expenses:
            #     mean_promo_expense = mean(promo_expenses.mapped("expense"))
            #     percent_promo_expense = mean_promo_expense / price
            
            # # берем коэф. из отчета о выплатах
            # percent_promo_expense = abs(tran_sums.filtered(lambda r: r.name == name).percent)
            # mean_promo_expense = price * percent_promo_expense
            # data.append(
            #     {
            #         "product_id": prod.id,
            #         "name": name,
            #         "kind": "percent",
            #         "category": fact_plan_match.get(name, "Unknown"),
            #         "percent": percent_promo_expense,
            #         "value": mean_promo_expense,
            #         "expected_value": exp_price * percent_promo_expense,
            #     }
            # )
            # затраты из отчета о выплатах
            for t_sum in tran_sums:
                if plan_component := fact_plan_match.get(t_sum.name):
                    percent = abs(t_sum.percent)
                    value = price * percent
                    exp_value = exp_price * percent
                    data.append(
                        {
                            "product_id": prod.id,
                            "name": t_sum.name,
                            "kind": "percent",
                            "category": plan_component,
                            "percent": percent,
                            "value": value,
                            "expected_value": exp_value,
                        }
                    )
                    total_expenses += value
            

            # # вознаграждение озон, последняя миля, логистика, обработка, эквайринг
            # if prod.trading_scheme == "FBO":
            #     ozon_com = prod.fbo_percent_expenses.filtered(
            #         lambda r: r.name.startswith("Процент")
            #     )
            #     last_mile = prod.fbo_fix_expenses_max.filtered(
            #         lambda r: r.name == "Последняя миля (FBO)"
            #     )
            #     logistics = prod.fbo_fix_expenses_max.filtered(
            #         lambda r: r.name == "Магистраль до (FBO)"
            #     )
            #     processing = prod.fbo_fix_expenses_max.filtered(
            #         lambda r: r.name == "Комиссия за сборку заказа (FBO)"
            #     )
            #     acquiring = prod.fbo_fix_expenses_max.filtered(
            #         lambda r: r.name == "Максимальная комиссия за эквайринг"
            #     )
            # else:
            #     ozon_com = prod.fbs_percent_expenses.filtered(
            #         lambda r: r.name.startswith("Процент")
            #     )
            #     last_mile = prod.fbs_fix_expenses_max.filtered(
            #         lambda r: r.name == "Последняя миля (FBS)"
            #     )
            #     logistics = prod.fbs_fix_expenses_max.filtered(
            #         lambda r: r.name == "Магистраль до (FBS)"
            #     )
            #     processing = prod.fbs_fix_expenses_max.filtered(
            #         lambda r: r.name.startswith("Максимальная комиссия за обработку")
            #     )
            #     acquiring = prod.fbs_fix_expenses_max.filtered(
            #         lambda r: r.name == "Максимальная комиссия за эквайринг"
            #     )

            # data.extend(
            #     [
            #         {
            #             "product_id": prod.id,
            #             "name": ozon_com.name,
            #             "description": ozon_com.discription,
            #             "kind": "percent",
            #             "category": "Вознаграждение Ozon",
            #             "percent": float(ozon_com.discription.replace("%", "")) / 100,
            #             "value": ozon_com.price,
            #             "expected_value": exp_price
            #             * float(ozon_com.discription.replace("%", ""))
            #             / 100,
            #         },
            #         {
            #             "product_id": prod.id,
            #             "name": last_mile.name,
            #             "kind": "percent",
            #             "category": "Последняя миля",
            #             "percent": last_mile.price / price,
            #             "value": last_mile.price,
            #             "expected_value": exp_price * last_mile.price / price,
            #         },
            #         {
            #             "product_id": prod.id,
            #             "name": logistics.name,
            #             "kind": "percent",
            #             "category": "Логистика",
            #             "percent": logistics.price / price,
            #             "value": logistics.price,
            #             "expected_value": logistics.price,
            #         },
            #         {
            #             "product_id": prod.id,
            #             "name": processing.name,
            #             "kind": "fix",
            #             "category": "Обработка",
            #             "percent": processing.price / price,
            #             "value": processing.price,
            #             "expected_value": processing.price,
            #         },
            #         {
            #             "product_id": prod.id,
            #             "name": acquiring.name,
            #             "kind": "percent",
            #             "category": "Эквайринг",
            #             "percent": acquiring.price / price,
            #             "value": acquiring.price,
            #             "expected_value": exp_price * acquiring.price / price,
            #         },
            #     ]
            # )
            # total_expenses += (
            #     ozon_com.price
            #     + last_mile.price
            #     + logistics.price
            #     + processing.price
            #     + acquiring.price
            # )
            ### расходы компании
            base_calc_company_expenses = prod.base_calculation_ids.filtered(
                lambda r: r.price_component_id.identifier.startswith("company_"))
            for i in base_calc_company_expenses:
                val = i.value
                data.append(
                    {
                        "product_id": prod.id,
                        "name": i.price_component_id.name,
                        "kind": "fix",
                        "category": "Расходы компании",
                        "percent": val / price,
                        "value": val,
                        "expected_value": exp_price * val / price,
                    }
                )
                total_expenses += val
            # налог
            tax_value = price * tax_percent
            expected_tax_value = exp_price * tax_percent
            data.append(
                {
                    "product_id": prod.id,
                    "name": "Налог",
                    "description": tax_description,
                    "kind": "percent",
                    "category": "Налог",
                    "percent": tax_percent,
                    "value": tax_value,
                    "expected_value": expected_tax_value,
                },
            )
            
            total_expenses += tax_value

            # рентабельность
            if prod.profitability_norm:
                prof_norm_percent = prod.profitability_norm.value
            else:
                prof_norm_percent = (price - total_expenses) / price
            prof_norm_value = price * prof_norm_percent
            expected_prof_norm_value = exp_price * prof_norm_percent
            data.append(
                {
                    "product_id": prod.id,
                    "name": "Доходность",
                    "kind": "percent",
                    "category": "Рентабельность",
                    "percent": prof_norm_percent,
                    "value": prof_norm_value,
                    "expected_value": expected_prof_norm_value,
                },
            )
            
            # инвест.затраты
            if prod.investment_expenses_id:
                inv_exp_percent = prod.investment_expenses_id.value
            else:
                inv_exp_percent = prof_norm_percent / 2
            inv_exp_value = price * inv_exp_percent
            expected_inv_exp_value = exp_price * inv_exp_percent
            data.append(
                {
                    "product_id": prod.id,
                    "name": "Investment",
                    "kind": "percent",
                    "category": "Investment",
                    "percent": inv_exp_percent,
                    "value": inv_exp_value,
                    "expected_value": expected_inv_exp_value,
                },
            )
            print(f"{idx} - All expenses were updated.")

        products.all_expenses_ids.unlink()
        for chunk in split_list_into_chunks_of_size_n(data, 50000):
            self.create(chunk)


class PromotionExpenses(models.Model):
    _name = "ozon.promotion_expenses"
    _description = "Затраты на продвижение товара Ozon"
    _order = "date desc"

    ad_campaign = fields.Char(string="Номер рекламной кампании", readonly=True)
    date = fields.Date(string="Дата", readonly=True)
    promotion_type = fields.Selection(
        [("search", "Продвижение в поиске")],
        string="Тип",
        readonly=True,
    )
    product_id = fields.Many2one("ozon.products", string="Товар Ozon", readonly=True)
    sku = fields.Char(string="SKU", readonly=True)
    order_id = fields.Char(string="ID заказа", readonly=True)
    posting_ids = fields.One2many(
        "ozon.posting", "promotion_expenses_id", string="Отправления", readonly=True
    )
    price = fields.Float(string="Цена продажи", readonly=True)
    qty = fields.Float(string="Кол-во единиц товара", readonly=True)
    total_price = fields.Float(string="Стоимость", readonly=True)
    percent_rate = fields.Float(string="Ставка, %", readonly=True)
    abs_rate = fields.Float(string="Ставка, ₽", readonly=True)
    expense = fields.Float(string="Расход, ₽", readonly=True)
