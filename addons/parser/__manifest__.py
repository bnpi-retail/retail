{
    'name': "Парсер",

    'summary': """Приложение для личного кабинета менеджеров""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "#",

    'category': 'Uncategorized',
    'version': '0.1',

    "depends": ["base", "retail", "ozon"],

    'data': [
        'security/ir.model.access.csv',

        'views/menu.xml',
        'views/api_tokens/menu.xml',
        'views/api_tokens/view.xml',

        'views/products/products_competitors.xml',
        'views/search/search_query_queue.xml',
        'views/import_file/import_file.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    "application": True,
    "sequence": 3
}
