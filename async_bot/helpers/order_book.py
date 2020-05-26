class MarketBook:
    def __init__(self, ticker_id, ticker_name):
        self.ticker_name = ticker_name
        self.ticker_id = ticker_id
        self.bids = []
        self.asks = []

    def __repr__(self):
        return self.ticker_name

    async def remove_item(self, side, price):
        if side == 'bid':
            for item in self.bids:
                if item[0] == price:
                    self.bids.remove(item)
        elif side == 'ask':
            for item in self.asks:
                if item[0] == price:
                    self.asks.remove(item)

    async def add_or_change(self, side, price, size):
        # bids have reverse sorting 10-9-8-7-...
        changed = False
        if side == 'bid':
            for item in self.bids:
                if item[0] == price:
                    item[1] = str(size)
                    changed = True
                    break
                elif item[0] < price:
                    self.bids.append([str(price), str(size)])
                    changed = True
                    self.bids.sort(reverse=True, key=lambda x: float(x[0]))
                    break
            if not changed:
                self.bids.append([str(price), str(size)])
                self.bids.sort(reverse=True, key=lambda x: float(x[0]))
        # asks have direct sorting 7-8-9-10-...
        elif side == 'ask':
            for item in reversed(self.asks):
                if item[0] == price:
                    item[1] = str(size)
                    changed = True
                    break
                elif item[0] < price:
                    self.asks.append([str(price), str(size)])
                    changed = True
                    self.asks.sort(key=lambda x: float(x[0]))
                    break
            if not changed:
                self.asks.append([str(price), str(size)])
                self.asks.sort(key=lambda x: float(x[0]))


class OrderBooks:
    def __init__(self):
        self.markets_by_id = {}

    async def add_market(self, ticker_id, ticker_name, asks, bids):
        market = await self.get_market_by_id(ticker_id)
        if market is not None:
            market.bids = bids
            market.asks = asks
        else:
            market = MarketBook(ticker_id, ticker_name)
            market.asks = asks
            market.bids = bids
        self.markets_by_id[ticker_id] = market

    async def get_market_by_id(self, ticker_id):
        return self.markets_by_id.get(ticker_id)





