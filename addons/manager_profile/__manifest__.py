{
    'name': "manager_profile",

    'summary': """Приложение для личного кабинета менеджеров""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base'],

    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/api_tokens/menu.xml',
        'views/api_tokens/view.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    "application": True,
    "sequence": 3
}
