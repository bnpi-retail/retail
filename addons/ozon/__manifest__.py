{
    "name": "Ozon",
    "summary": """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    "description": """
        Long description of module's purpose
    """,
    "author": "My Company",
    "website": "https://www.yourcompany.com",
    "category": "Uncategorized",
    "version": "0.2.1",
    "depends": ["base", "retail"],
    # always loaded
    "data": [
        ### security
        "security/price/price_history/ir.model.access.csv",
        "security/price/fix_expenses/ir.model.access.csv",
        "security/price/cost/ir.model.access.csv",
        "security/price/pricing/ir.model.access.csv",
        "security/price/name_competitors/ir.model.access.csv",
        "security/price/profitability_norm/profitability_norm/ir.model.access.csv",
        "security/price/profitability_norm/profitability_norm_wizard/ir.model.access.csv",
        "security/price/price_comparison/ir.model.access.csv",
        "security/products/ir.model.access.csv",
        "security/products/tracked_search_queries/ir.model.access.csv",
        "security/categories/categories/ir.model.access.csv",
        "security/commissions/fee_ozon/ir.model.access.csv",
        "security/import/import/ir.model.access.csv",
        "security/competitors/products_competitors/ir.model.access.csv",
        "security/competitors/price_competitors/ir.model.access.csv",
        "security/competitors/analysis_competitors/ir.model.access.csv",
        "security/competitors/analysis_competitors_record/ir.model.access.csv",
        "security/competitors/successful_product_competitors/ir.model.access.csv",
        "security/competitors/competitor_sale/ir.model.access.csv",
        "security/competitors/competitor_seller/ir.model.access.csv",
        "security/search_queries/search_queries/ir.model.access.csv",
        "security/transaction/ir.model.access.csv",
        "security/stock/ir.model.access.csv",
        "security/product_fee/ir.model.access.csv",
        "security/sale/ir.model.access.csv",
        "security/tasks/ir.model.access.csv",
        "security/indirect_percent_expenses/ir.model.access.csv",
        "security/supplementary_categories/ir.model.access.csv",
        "security/posting/ir.model.access.csv",
        "security/warehouse/ir.model.access.csv",
        "security/fbo_supply_order/ir.model.access.csv",
        "security/action/ir.model.access.csv",
        "security/indicator/ir.model.access.csv",
        "security/reports/ir.model.access.csv",
        "security/settings/ir.model.access.csv",
        "security/price/investment_expenses/investment_expenses/ir.model.access.csv",
        "security/price/investment_expenses/investment_expenses_wizard/ir.model.access.csv",
        "security/history_of_product_positions/history_of_product_positions/ir.model.access.csv",
        "security/price/all_expenses/ir.model.access.csv",
        "security/price/promotion_expenses/ir.model.access.csv",
        "security/ir.model.access.csv",
        ### views
        "views/dicts/profitability_norm.xml",
        "views/income_expenses/transactions.xml",
        "views/income_expenses/sale.xml",
        "views/income_expenses/promotion_expenses.xml",
        "views/income_expenses/fee_ozon.xml",
        "views/income_expenses/product_fee.xml",
        "views/history/price_history.xml",
        "views/history/stocks.xml",
        "views/history/analysis_data.xml",
        "views/history/history_of_product_positions.xml",
        "views/plan/price_component.xml",
        "views/plan/price_component_match.xml",
        "views/plan/base_calculation.xml",
        "views/plan/draft_product.xml",
        "views/plan/mass_calculator.xml",
        "views/reports/indirect_percent_expenses.xml",
        "views/reports/sales_report_by_category.xml",
        "views/reports/realisation_report.xml",
        "views/analytics/ozon_report_interest_views.xml",
        "views/analytics/abs_analysis.xml",
        "views/analytics/bcg_matrix.xml",
        "views/manager/mass_pricing.xml",
        "views/manager/indicator_monitoring.xml",
        "views/manager/indicator_report.xml",
        "views/manager/tasks.xml",
        "views/manager/successful_products_competitors.xml",
        "views/competitors/products_competitors.xml",
        "views/competitors/price_competitors.xml",
        "views/competitors/analysis_competitors.xml",
        "views/competitors/ozon_report_category_market_share_views.xml",
        "views/competitors/competitor_seller_view.xml",
        "views/competitors/competitor_other_marketplace.xml",
        # "views/competitors/our_price_history.xml",
        "views/actions/action.xml",
        "views/actions/action_candidate.xml",
        "views/products_logistics/posting.xml",
        "views/products_logistics/fbo_supply_order.xml",
        "views/products_logistics/fbo_supply_order_product.xml",
        "views/dicts/pricing_strategy.xml",
        "views/dicts/investment_expenses.xml",
        "views/dicts/categories.xml",
        "views/dicts/supplementary_categories.xml",
        "views/dicts/logistics_tariff.xml",
        "views/dicts/warehouse.xml",
        "views/dicts/search_queries.xml",
        "views/dicts/tracked_search_queries.xml",
        "views/dicts/settings.xml",
        "views/import/import.xml",
        "views/import/mass_data_import_views.xml",
        "views/import/mass_data_import_log_views.xml",
        "views/import/imported_report.xml",
        "views/chat_gpt/lots_for_gpt.xml",
        "views/products/wizards.xml",
        "views/products/products.xml",
        "views/menu.xml",
        # cron
        "crone/ir_cron_data.xml",
    ],
    "assets": {
        "web.assets_backend": {
                "ozon/static/src/css/price_comparison.css",
            }
        },
    "demo": [
        "demo/demo.xml",
    ],
    "application": True,
    "sequence": 1,
}
