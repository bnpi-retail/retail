import time
import undetected_chromedriver as uc

from odoo import http
from odoo.http import request
from odoo.http import Response

from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service



class Start:
    def __init__(self):
        self.chrome_driver_path = './chromedriver-linux64/chromedriver'

    def start(self):
        service = Service(executable_path=self.chrome_driver_path)
        driver = uc.Chrome(service=service)
        return driver

    def wait_load_page(self, driver):
        attemp = 0
        len_ads = 0
        while len_ads == 0:
            if attemp == 5:
                return False
            time.sleep(1)
            ads = self.get_ads(driver.page_source)
            len_ads = len(ads)
            attemp += 1

        print(f'Page loaded! {len(ads)}')
        return True

    def get_ads(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        ads = soup.find_all('div', class_='iv5 v5i')
        return ads

    def parsing(self, html):
        ads = self.get_ads(html)
        
        products = []

        for ad in ads[0:12]:
            link_element = ad.find('a', class_='si7 tile-hover-target')
            if link_element:
                link = link_element.get('href')
            else:
                link = None

            info_element = ad.find('div', class_='iv6')
            if info_element:
                price_element = info_element.find('span', class_='c3119-a1 tsHeadline500Medium c3119-b9')
                price = price_element.text.replace('\u2009₽', '') if price_element else None

                price_without_sale_element = info_element.find('span', class_='c3119-a1 tsBodyControl400Small c3119-b0')
                price_without_sale = price_without_sale_element.text.replace('\u2009₽', '') if price_without_sale_element else None

                sale_element = info_element.find('span', class_='tsBodyControl400Small c3119-a2 c3119-a7 c3119-b1')
                sale = sale_element.text.replace('%', '') if sale_element else None

                name_ad_element = info_element.find('span', class_='tsBody500Medium')
                name_ad = name_ad_element.text if name_ad_element else None

            product = {
                'link': link,
                'price': price,
                'price_without_sale': price_without_sale,
                'sale': sale,
                'name_ad': name_ad
            }
            products.append(product)
        return products

    def get_sku(self, html):
        try:
            soup = BeautifulSoup(html, 'html.parser')
            sku_element = soup.find('span', class_='kn5 nk5')
            sku = sku_element.text.replace('Код товара: ', '')
            return sku
        except Exception as e:
            print(e)
            return False
        
    def get_add_info(self, products):
        for product in products:
            link = product['link']

            link = 'https://www.ozon.ru' + link
            
            sku = False
            global_attemp = 0
            while not sku:
                driver = self.start()
                driver.get(link)

                attemp = 0
                while attemp < 4:
                    time.sleep(1)
                    sku = self.get_sku(driver.page_source)
                    attemp += 1
                    global_attemp += 1

                driver.quit() 
                if global_attemp == 5: break

            print(sku)
            product['sku'] = sku

    def get_url(self, url):
        status = False
        while not status:
            driver = self.start()
            driver.get(url)
            status = self.wait_load_page(driver)
            if not status: driver.quit() 

        products = self.parsing(driver.page_source)
        driver.quit()

        print(f'{len(products)}--{products[0]}')
        self.get_add_info(products)


class SeleniumOozonParser(http.Controller):
    @http.route("/ozon/run_selenium_parser", auth="user", csrf=False, methods=["POST"])
    def run_selenium_parser(self, **kwargs):
        try:
            parser = Start()
            data = parser.get_url(url='https://www.ozon.ru/search/?from_global=true&text=%D0%B0%D0%B2%D1%82%D0%BE%D1%81%D1%82%D0%B8%D0%BB%D1%8C%20%D0%BD%D0%B0%D0%BA%D0%BB%D0%B5%D0%B9%D0%BA%D0%B0')
            return request.jsonify(data)
        except Exception as e:
            return Response(status=500, json={'error': str(e)})

