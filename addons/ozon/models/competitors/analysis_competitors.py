from odoo import models, fields, api


class AnalysisCompetitorsLine(models.Model):
    _name = 'ozon.analysis_competitors_record'
    _description = 'Анализ конкурента'

    name = fields.Char(string='Наименование')
    number = fields.Char(string='Место объявления')
    price = fields.Float(string='Цена')
    price_without_sale = fields.Float(string='Цена без скидки')
    price_with_card = fields.Float(string='Цена по карте Ozon')
    analysis_id = fields.Many2one('ozon.analysis_competitors', string='Анализ конкурента')
    ad = fields.Reference([
        ('ozon.products', 'Лот'),
        ('ozon.products_competitors', 'Товар конкурента'),
    ], string='Товар')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            display_name = f"{record.number} - {record.name}"
            result.append((record.id, display_name))
        return result


class AnalysisCompetitors(models.Model):
    _name = 'ozon.analysis_competitors'
    _description = 'Анализ конкурентов'

    timestamp = fields.Datetime(string='Дата и время', 
                                default=fields.Datetime.now,
                                readonly=True)

    competitor_record = fields.One2many('ozon.analysis_competitors_record', 
                                        'analysis_id', string='Конкуренты')

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            competitor_name = record.competitor_record and record.competitor_record[0].name or ''
            display_name = f"{record.id} - {record.timestamp} - {competitor_name}"
            result.append((record.id, display_name))
        return result
