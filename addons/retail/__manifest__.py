{
    "name": "retail",
    "summary": """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    "description": """
        Long description of module's purpose
    """,
    "author": "StrunkGroove",
    "website": "#",
    "category": "Retail",
    "version": "0.1",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "security/import_file/ir.model.access.csv",
        "security/products/ir.model.access.csv",
        "security/seller/ir.model.access.csv",
        "security/cost_price/ir.model.access.csv",
        "security/categories/ir.model.access.csv",
        # 'views/views.xml',
        "views/menu.xml",
        "views/cost_price/menu.xml",
        "views/cost_price/acts.xml",
        "views/cost_price/cost_price.xml",
        "views/cost_price/type_acts.xml",
        "views/cost_price/act_products.xml",
        "views/import/import.xml",
        "views/products/products.xml",
        "views/seller/seller.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ],
    "application": True,
    "sequence": 1
}
