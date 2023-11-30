# retail
## TODO:
- [x] Запросить все товары из Ozon API и сохранить в файл
- [x] На странице ozon.import при выборе "Данные для загрузки" = "Товары Ozon" 
показать кнопку "Выгрузить товары из Ozon API" > скачивается файл
- [x] В модуль ozon.import добавить возможность импортировать файл с данными о товарах из Ozon API
- [x] Импортируя такой файл, заполнить модель Лот (ozon.products)
- [x] индекс локализации и пункт приема товара сделать пустыми
- [ ] брать из api тажке цены и заполнять модель. Какую?
- [ ] заполнить модель ozon.fee коммиссиями по категориям (через ozon.import комиссии)
- [ ] Если товар и в FBS, и в FBO, то его записывать как две записи в ozon.products, при этом в retail.products остается только один товар с таким id
- [ ] Включить загрузку всех товаров (удалить break в ozon_api)
- [x] api-key и client-id через env_variables
- [ ] push, pull request

Опционально:
- [ ] Взять id и attributes (json) и сохранить в базу
- [ ] Потом из этого json уже доставать нужные значения для других столбцов