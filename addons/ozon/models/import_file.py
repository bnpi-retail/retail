import base64
import xml.etree.ElementTree as ET
import magic
import mimetypes
from odoo import models, fields, api, exceptions

import os
from odoo import http
from werkzeug.wrappers import Response
from io import BytesIO


class ImportFile(models.Model):
    _name = 'ozon.import_file'
    _description = 'Импорт'

    data_for_download = fields.Selection(
        [
            ('index_local', 'Индекс локализации'),
            ('logistics_cost', 'Стоимость логистики'),
            ('fees', 'Комиссии'),
        ], 
        string='Данные для загрузки'
    )

    file = fields.Binary(
        attachment=True,
        help='Выбрать файл'
    )

    def get_file_mime_type(self, file_content):
        mime = magic.Magic()
        file_type = mime.from_buffer(file_content)
        return file_type

    @api.model
    def create(self, values):
        if not 'file' in values or not values['file']:
            raise exceptions.ValidationError('Отсутствует файл.')

        if not 'data_for_download' in values or not values['data_for_download']:
            raise exceptions.ValidationError("Необходимо выбрать 'данные для загрузки'")
        
        content = base64.b64decode(values['file'])
        mime_type = self.get_file_mime_type(content)
        mime_type = mime_type.lower()

        format = mime_type

        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            pass

        if 'csv' in mime_type:
            content = content.decode('utf-8')
            lines = content.split('\n')

            if values['data_for_download'] == 'index_local':
                localization_index = self.env['ozon.localization_index']

                for line in lines:
                    if line:
                        range_str, value_str = line.split(',')
                        range_start, range_end = map(int, range_str.split('-'))
                        value = float(value_str)

                        localization_index.create({
                            'lower_threshold': range_start,
                            'upper_threshold': range_end,
                            'coefficient': value,
                        })
                        
            elif values['data_for_download'] == 'logistics_cost':
                logistics_ozon = self.env['ozon.logistics_ozon']

                for line in lines:
                    if line:
                        trading_scheme, volume, price = line.split(',')
                        volume = float(volume)
                        price = float(price)

                        logistics_ozon.create({
                            'trading_scheme': trading_scheme,
                            'volume': volume,
                            'price': price,
                        })

            elif values['data_for_download'] == 'fees':
                ozon_fee = self.env['ozon.ozon_fee']
                categories = self.env['retail.categories']

                for line in lines:
                    if line:
                        name, type, value, name_categories, name_on_platform, name_platform = line.split(',')
                        categorie = categories.create({
                            'name_categories': name_categories,
                            'name_on_platform': name_on_platform,
                            # 'name_platform': name_platform,
                        })

                        value = float(value)

                        ozon_fee.create({
                            'name': name,
                            'category': categorie.id,
                            'type': type,
                            'value': value,
                        })

        return super(ImportFile, self).create(values)
