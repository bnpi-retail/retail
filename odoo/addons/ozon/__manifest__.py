# -*- coding: utf-8 -*-
{
    'name': "ozon",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base', 'retail'],

    # always loaded
    'data': [
        ### security
        'security/price/count_price/ir.model.access.csv',
        'security/price/price_history/ir.model.access.csv',
        'security/price/fix_expenses/ir.model.access.csv',
        'security/price/cost/ir.model.access.csv',
        'security/price/pricing/ir.model.access.csv',
        'security/price/name_competitors/ir.model.access.csv',

        'security/lots/lots/ir.model.access.csv',

        'security/categories/categories/ir.model.access.csv',

        'security/commissions/local_index/ir.model.access.csv',
        'security/commissions/fee_ozon/ir.model.access.csv',
        'security/commissions/logistics_price/ir.model.access.csv',

        'security/movement_of_funds/movement_of_funds/ir.model.access.csv',

        'security/import/import/ir.model.access.csv',

        'security/competitors/products_competitors/ir.model.access.csv',
        'security/competitors/price_competitors/ir.model.access.csv',

        'security/count_insurance_percent/count_insurance_percent/ir.model.access.csv',

        'security/search_queries/search_queries/ir.model.access.csv',

        'security/issue_report/issue_report/ir.model.access.csv',
        'security/issue_report/issue_report_products/ir.model.access.csv',
        'security/issue_report/issue_report_products_additional_info/ir.model.access.csv',
        'security/issue_report/name_additional_info/ir.model.access.csv',

        ### views
        'views/menu.xml',
        
        'views/price/menu.xml',
        'views/price/count_price.xml',
        'views/price/price_history.xml',
        'views/price/our_fix_price.xml',
        'views/price/pricing.xml',

        'views/lots/lots.xml',

        'views/categories/categories.xml',

        'views/commissions/menu.xml',
        'views/commissions/local_index.xml',
        'views/commissions/fee_ozon.xml',
        'views/commissions/logistics_price.xml',

        'views/movement_of_funds/movement_of_funds.xml',

        'views/import/import.xml',

        'views/competitors/menu.xml',
        'views/competitors/products_competitors.xml',
        'views/competitors/price_competitors.xml',
        
        'views/count_insurance_percent/menu.xml',
        'views/count_insurance_percent/count_insurance_percent.xml',
        
        'views/actions/assign_an_insurance_coefficient.xml',

        'views/issue_report/menu.xml',
        'views/search_queries/search_queries.xml',
        'views/issue_report/issue_report.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
}
