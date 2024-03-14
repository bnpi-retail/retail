import logging
from collections import defaultdict

from datetime import datetime, timedelta, date
from odoo import models, fields, api
from .drawing_graphs import DrawGraph as df

logger = logging.getLogger(__name__)


class Categories(models.Model):
    _name = "ozon.categories"
    _description = "Категории Ozon"

    name_categories = fields.Char(string="Название", readonly=True)
    c_id = fields.Integer(string="Идентификатор", readonly=True, index=True)
    insurance = fields.Float(string="Страховой коэффициент, %")

    category_manager = fields.Many2one("res.users")
    bcg_matrix_last_update = fields.Datetime()
    abc_group_last_update = fields.Datetime()

    category_total_price = fields.Float(string="Сумма цен товаров категории в продаже")
    category_total_marketing_price = fields.Float(string="Сумма цен для покупателя товаров категории в продаже")
    price_difference = fields.Float(
        string="Cоотношение между нашей ценой и ценой для покупателя")
    is_price_difference_computed = fields.Boolean()

    ozon_products_ids = fields.One2many('ozon.products', 'categories')

    # revenue and expenses
    ozon_report_products_revenue_expenses_ids = fields.One2many(
        'ozon.report.products_revenue_expenses',
        'ozon_categories_id',
    )
    ozon_report_products_revenue_expenses_theory_ids = fields.One2many(
        'ozon.report.products_revenue_expenses_theory',
        'ozon_categories_id',
    )
    period_start = fields.Date(string="Период с", default=date.today() - timedelta(days=31))
    period_finish = fields.Date(string="по", default=date.today() - timedelta(days=1))
    period_preset = fields.Selection([
        ('month', '1 месяц'), ('2month', '2 месяца'), ('3month', '3 месяца')
    ])
    is_promotion_data_correct = fields.Boolean()

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

    def _get_sum_value_and_qty_from_transaction_value_by_product(self, name: str, ids: Iterable = None) -> tuple:
        if ids is None:
            ids = (self.id, )
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
        self.env.cr.execute(query, (self.period_start, self.period_finish, tuple(ids), name))
        sum_value_and_qty = self.env.cr.fetchone()
        sum_value = sum_value_and_qty[0] if sum_value_and_qty and sum_value_and_qty[0] else 0
        qty = sum_value_and_qty[1] if sum_value_and_qty else 0

        return sum_value, qty

    def calculate_sales_revenue_for_period(self) -> tuple[dict, dict, float, float, float]:
        revenue, sales_qty = self._get_sum_value_and_qty_from_transaction_value_by_product('Сумма за заказы')
        category_products_ids = self.categories.ozon_products_ids.ids
        category_revenue, cat_qty = self._get_sum_value_and_qty_from_transaction_value_by_product(
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
            res = self._get_sum_value_and_qty_from_transaction_value_by_product(name)
            category_value, cat_qty = self._get_sum_value_and_qty_from_transaction_value_by_product(
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
            res = self._get_sum_value_and_qty_from_transaction_value_by_product(name)
            category_value, cat_qty = self._get_sum_value_and_qty_from_transaction_value_by_product(
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
            if qty:
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
            elif trading_scheme == "FBS, FBO":
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
            elif trading_scheme == "FBS, FBO":
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

    def calc_total_sum(self, name: str):
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
        self.env.cr.execute(query, (self.period_start, self.period_finish, name))
        total_sum_value = self.env.cr.fetchone()
        return total_sum_value[0] if total_sum_value and total_sum_value[0] else 0


    @api.model
    def _name_search(
        self, name="", args=None, operator="ilike", limit=10, name_get_uid=None
    ):
        args = list(args or [])
        if name:
            args += [("name_categories", operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    def action_compute_average_prices_difference(self):
        for record in self:
            query = """
                    SELECT
                         SUM(price) as total_price,
                         SUM(marketing_price) as total_marketing_price
                    FROM
                        ozon_products
                    WHERE
                        categories = %s
                        AND
                        is_selling = %s
            """
            self.env.cr.execute(query, (record.id, True))
            result = self.env.cr.fetchone()

            total_price = result[0] if result and result[0] else 0.00001
            total_marketing_price = result[1] if result and result[1] else 0

            if result and (result[0] or result[1]):
                record.price_difference = (total_price - total_marketing_price) / total_price

            record.category_total_price = total_price
            record.category_total_marketing_price = total_marketing_price

            record.is_price_difference_computed = True


class GenerateUrlForDownloadGrpahData(models.Model):
    _inherit = "ozon.categories"

    def get_url(self, model_name, record_id, field_name):
        return f'/web/content_text?model={model_name}&id={record_id}&field={field_name}'

    def get_download_url(self, field_name):
        model_name = self._name
        record_id = self.id
        url = self.get_url(model_name, record_id, field_name)
        return url


class GraphSaleThisYear(models.Model):
    _inherit = "ozon.categories"

    img_data_sale_this_year = fields.Text(string="Json data filed")
    img_sale_this_year = fields.Binary(string="График продаж за текущий год")

    def download_data_sale_this_year(self):
        field_name = "img_data_sale_this_year"
        url = self.get_download_url(field_name)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


class GraphSaleLastYear(models.Model):
    _inherit = "ozon.categories"

    img_data_sale_last_year = fields.Text(string="Json data filed")
    img_sale_last_year = fields.Binary(string="График продаж за прошлый год")

    def download_data_sale_last_year(self):
        field_name = "img_data_sale_last_year"
        url = self.get_download_url(field_name)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


class GraphInterest(models.Model):
    _inherit = "ozon.categories"

    img_data_analysis_data_this_year = fields.Text(string="Json data filed")
    img_analysis_data_this_year = fields.Binary(string="График интереса текущий год")

    def download_data_analysis_data_this_year(self):
        field_name = "img_data_analysis_data_this_year"
        url = self.get_download_url(field_name)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


class ActionGraphs(models.Model):
    _inherit = "ozon.categories"

    def action_draw_graphs_by_categories(self, auto=None):
        logger.info('draw_sale_this_year')
        self.draw_sale_this_year()
        logger.info('draw_sale_last_year')
        self.draw_sale_last_year()
        logger.info('draw_graph_interest')
        self.draw_graph_interest()
        logger.info('draw_graphs_products')

        self.draw_graphs_products(self.ozon_products_ids, auto)

        return True

    def draw_sale_this_year(self):
        year = self._get_year()

        data_for_send = {}

        categorie_record = self[0]

        products_records = self.env["ozon.products"].search(
            [
                ("categories", "=", categorie_record.id),
                # ("is_alive", "=", True),
                # ("is_selling", "=", True),
            ]
        )

        for product_record in products_records:
            sale_records = self.env["ozon.sale"].search(
                [
                    ("product", "=", product_record.id),
                    ("date", ">=", f"{year}-01-01"),
                    ("date", "<=", f"{year}-12-31"),
                ]
            )

            if not sale_records:
                continue

            graph_data = {"dates": [], "values": []}

            for sale_record in sale_records:
                graph_data["dates"].append(sale_record.date.strftime("%Y-%m-%d"))
                graph_data["values"].append(sale_record.qty)

            data_for_send[product_record.id] = graph_data

        payload = {
            "model": "categorie_sale_this_year",
            "categorie_id": categorie_record.id,
            "data": data_for_send,
        }

        bytes_plot, data_current = df().post(payload)
        self.img_sale_this_year, self.img_data_sale_this_year = bytes_plot, data_current

        return products_records

    def draw_sale_last_year(self):
        year = self._get_year() - 1

        data_for_send = {}

        categorie_record = self[0]

        products_records = self.ozon_products_ids

        for product_record in products_records:
            sale_records = self.env["ozon.sale"].search(
                [
                    ("product", "=", product_record.id),
                    ("date", ">=", f"{year}-01-01"),
                    ("date", "<=", f"{year}-12-31"),
                ]
            )

            if not sale_records:
                continue

            graph_data = {"dates": [], "values": []}

            for sale_record in sale_records:
                graph_data["dates"].append(sale_record.date.strftime("%Y-%m-%d"))
                graph_data["values"].append(sale_record.qty)

            data_for_send[product_record.id] = graph_data

        payload = {
            "model": "categorie_sale_last_year",
            "categorie_id": categorie_record.id,
            "data": data_for_send,
        }

        bytes_plot, data_current = df().post(payload)
        self.img_sale_last_year, self.img_data_sale_last_year = bytes_plot, data_current

        return products_records

    def draw_graph_interest(self):
        year = self._get_year()

        data_for_send = defaultdict(lambda: {
            "hits_view": 0,
            "hits_tocart": 0,
        })

        categorie_record = self[0]

        products_ids = self.ozon_products_ids.ids

        analysis_data_records = self.env["ozon.analysis_data"].search(
            [
                ("product", "in", products_ids),
                ("date", ">=", f"{year}-01-01"),
                ("date", "<=", f"{year}-12-31"),
            ]
        )

        graph_data = {"dates": [], "hits_view": [], "hits_tocart": []}

        for analysis_data_record in analysis_data_records:
            average_date = analysis_data_record.date
            data_for_send[average_date.strftime("%Y-%m-%d")]["hits_view"] += analysis_data_record.hits_view
            data_for_send[average_date.strftime("%Y-%m-%d")]["hits_tocart"] += analysis_data_record.hits_tocart

        for date, vals in data_for_send.items():
            graph_data['dates'].append(date)
            graph_data['hits_view'].append(vals['hits_view'])
            graph_data['hits_tocart'].append(vals['hits_tocart'])

        data_ = {1: graph_data}

        payload = {
            "model": "categorie_analysis_data",
            "categorie_id": categorie_record.id,
            "data": data_,
        }

        logger.info("draw_graph_interest: df().post(payload)")
        bytes_plot, data_views, data_tocart = df().post(payload)

        self.img_analysis_data_this_year = bytes_plot
        self.img_data_analysis_data_this_year = {
            "hits_view": data_views,
            "hits_tocart": data_tocart,
        }

    def draw_graphs_products(self, products_records, auto):
        logger.info(f"All records: {len(products_records)}")

        for index, product_record in enumerate(products_records):
            if auto:
                last_plots_update = product_record.last_plots_update
                logger.info(last_plots_update)
                if last_plots_update and last_plots_update + timedelta(hours=12) > datetime.now():
                    continue
            product_record.action_draw_graphs()
            product_record.last_plots_update = datetime.now()

            logger.info(index + 1)

    def _get_year(self) -> str:
        return datetime.now().year


class NameGetCustom(models.Model):
    _inherit = "ozon.categories"

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.name_categories))
        return result

class CategoryFees(models.Model):
    _inherit = "ozon.categories"

    def _trading_scheme_fees(self):
        ozon_fee_recs = self.env["ozon.ozon_fee"].search([("category", "=", self.id)])
        return {fee.name: fee.value for fee in ozon_fee_recs}