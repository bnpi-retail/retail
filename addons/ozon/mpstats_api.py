def get_yesterday_stock_sales_price(sku):
    url = f"https://mpstats.io/api/oz/get/item/{sku}/sales"
        res = self._get_token_mpstats()
        if res:
            raise ValueError(f"{res['response']}")
        headers = {
            "X-Mpstats-TOKEN": self.token_mpstats,
            "Content-Type": "application/json",
        }

        today, yesterday = self.get_days()
        params = {
            "d1": today,
            "d2": yesterday,
        }

        # response = requests.get(url, headers=headers, params=params)
        response = requests.get(url, headers=headers)