import os
from SmartApi import SmartConnect
import pyotp
from typing import Dict, Any, List

class AngelOneClient:
    def __init__(self, api_key: str, client_id: str, password: str, totp_secret: str):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_secret = totp_secret
        self.smart_api = SmartConnect(api_key=self.api_key)
        self.session_data = None

    def login(self) -> Dict[str, Any]:
        """Authenticates with Angel One SmartAPI."""
        totp = pyotp.TOTP(self.totp_secret).now()
        self.session_data = self.smart_api.generateSession(self.client_id, self.password, totp)
        
        if self.session_data.get('status') is False:
            raise Exception(f"Login failed: {self.session_data.get('message')}")
        
        return self.session_data

    def get_profile(self) -> Dict[str, Any]:
        """Fetches the user profile."""
        return self.smart_api.getProfile(self.session_data['data']['jwtToken'])

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Fetches the current holdings."""
        return self.smart_api.holding()

    def get_positions(self) -> List[Dict[str, Any]]:
        """Fetches current positions."""
        return self.smart_api.position()

    def place_order(self, variety: str, symboltoken: str, exchange: str, transactiontype: str, 
                    ordertype: str, producttype: str, duration: str, quantity: str, 
                    price: str = "0", squareoff: str = "0", stoploss: str = "0", 
                    trailingstoploss: str = "0") -> Dict[str, Any]:
        """Places an order."""
        order_params = {
            "variety": variety,
            "symboltoken": symboltoken,
            "exchange": exchange,
            "transactiontype": transactiontype,
            "ordertype": ordertype,
            "producttype": producttype,
            "duration": duration,
            "price": price,
            "squareoff": squareoff,
            "stoploss": stoploss,
            "trailingstoploss": trailingstoploss,
            "quantity": quantity
        }
        return self.smart_api.placeOrder(order_params)

    def get_order_book(self) -> List[Dict[str, Any]]:
        """Fetches the order book."""
        return self.smart_api.orderBook()

    def get_historical_data(self, exchange: str, symboltoken: str, interval: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """Fetches historical candle data from Angel One."""
        try:
            params = {
                "exchange": exchange,
                "symboltoken": symboltoken,
                "interval": interval,
                "fromdate": from_date,
                "todate": to_date
            }
            response = self.smart_api.getCandleData(params)
            if response.get("status") and response.get("data"):
                # The API returns a list of lists: [timestamp, open, high, low, close, volume]
                # We convert it to a list of dicts for consistency with the rest of the app.
                history = []
                for candle in response["data"]:
                    history.append({
                        "timestamp": candle[0],
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5])
                    })
                return history
            return []
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return []
    def get_market_data(self, mode: str, exchange_tokens: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Fetch live market data.

        mode:
            LTP
            OHLC
            FULL

        exchange_tokens example:
        {
            "NSE": ["3045"],
            "NFO": ["99926000"]
        }
        """
        try:
            params = {
                "mode": mode,
                "exchangeTokens": exchange_tokens
            }

            response = self.smart_api.getMarketData(params)
            return response

        except Exception as e:
            print(f"Error fetching market data: {e}")
            return {}