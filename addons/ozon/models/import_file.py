import base64
import magic
import xml.etree.ElementTree as ET

from odoo import models, fields, api, exceptions


class ImportFile(models.Model):
    _name = 'ozon.import_file'
    _description = 'Импорт'

    timestamp = fields.Date(string='Дата импорта', 
                            default=fields.Date.today,
                            readonly=True)
    
    data_for_download = fields.Selection([('index_local', 'Индекс локализации'),
                                          ('logistics_cost', 'Стоимость логистики'),
                                          ('fees', 'Комиссии'),
                                          ('excel_fbo', 'Excel FBO'),
                                          ('excel_fbs', 'Excel FBS'),
                                          ('fee_fix', 'Excel Fix')], 
                                          string='Данные для загрузки')
    
    file = fields.Binary(attachment=True, 
                        string='Файл для загрузки сових данных', 
                        help='Выбрать файл') 


    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            id = record.id
            name = f"Загруженный файл № {id}"
            result.append((id, name))
        return result
    

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

            logistics_ozon = self.env['ozon.logistics_ozon']

            if values['data_for_download'] == 'excel_fbo':
                logistics_ozon = self.env['ozon.logistics_ozon']

                for entry in root.findall('entry'):
                    volume = entry.find('volume').text
                    rate = entry.find('rate').text

                    logistics_ozon.create({
                        'trading_scheme': 'FBO',
                        'volume': volume,
                        'price': rate,
                    })
            
            elif values['data_for_download'] == 'excel_fbs':
                logistics_ozon = self.env['ozon.logistics_ozon']

                for entry in root.findall('entry'):
                    volume = entry.find('volume').text
                    rate = entry.find('rate').text

                    logistics_ozon.create({
                        'trading_scheme': 'FBS',
                        'volume': volume,
                        'price': rate,
                    })

            elif values['data_for_download'] == 'fee_fix':
                ozon_fee = self.env['ozon.ozon_fee']

                for entry in root.findall('entry'):
                    ppt = entry.find('PPT').text
                    volume = entry.find('volume').text

                    if ppt == 'ППЗ':
                        ppt_in_selections = 'PC'
                    elif ppt == 'ПВЗ':
                        ppt_in_selections = 'PP'
                    elif ppt == 'СЦ':
                        ppt_in_selections = 'SC'
                    elif ppt == 'ТСЦ':
                        ppt_in_selections = 'TSC'
                     
                    ozon_fee.create({
                        # 'name': categorie.id,
                        'value': volume,
                        # 'category': categorie.id,
                        'type': 'fix',
                        'delivery_location': ppt_in_selections,
                    })

            elif values['data_for_download'] == 'fees':
                ozon_fee = self.env['ozon.ozon_fee']
                categories = self.env['ozon.categories']

                for category in root.findall('Category'):
                    name = category.find('Name').text
                    fbo_commission = category.find('FBO_Commission').text.replace('%', '')
                    fbs_commission = category.find('FBS_Commission').text.replace('%', '')
                    rfbs_commission = category.find('RFBS_Commission').text.replace('%', '')
                    fbo_last_mile_percentage = category.find('FBO_Last_Mile_Percentage').text if category.find('FBO_Last_Mile_Percentage') is not None else ""
                    fbo_last_mile_min = category.find('FBO_Last_Mile_Min').text if category.find('FBO_Last_Mile_Min') is not None else ""

                    categorie = categories.search([('name_categories', '=', name)])

                    value = {
                        'name': name,
                        'value': fbo_commission,
                        'category': categorie.id,
                        'type': 'percent',
                        'trading_scheme': 'FBO',
                    }
                    if categorie:
                        value['category'] = categorie.id
                    ozon_fee.create(value)

                    value = {
                        'name': name,
                        'value': fbs_commission,
                        'category': categorie.id,
                        'type': 'percent',
                        'trading_scheme': 'FBS',
                    }
                    if categorie:
                        value['category'] = categorie.id
                    ozon_fee.create(value)

                    value = {
                        'name': name,
                        'value': rfbs_commission,
                        'category': categorie.id,
                        'type': 'percent',
                        'trading_scheme': 'rFBS',
                    }
                    if categorie:
                        value['category'] = categorie.id
                    ozon_fee.create(value)

            return super(ImportFile, self).create(values)    
        except ET.ParseError:
            pass
        
        content_old = content
        content = content.decode('utf-8')
        lines = content.split('\n')

        if 'csv' in mime_type:

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
                            'percent': (value-1)*100 ,
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

        if values['data_for_download'] == 'excel':

            import xlrd
            content_decoded = content_old.decode('latin-1')
            workbook = xlrd.open_workbook(file_contents=content_decoded)

            sheet = workbook.sheet_by_index(0)

            for row_idx in range(sheet.nrows):
                for col_idx in range(sheet.ncols):
                    cell_value = sheet.cell_value(row_idx, col_idx)
                    print(cell_value)

        return super(ImportFile, self).create(values)
