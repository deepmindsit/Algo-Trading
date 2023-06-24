

class ApiTerminal():

    flatTradeBaseUrl = "https://piconnect.flattrade.in/PiConnectTP"
    flatTradeApi = {
        "userDetails": f"{flatTradeBaseUrl}/UserDetails",
        "placeOrder": f"{flatTradeBaseUrl}/PlaceOrder",
        "getQuotes": f"{flatTradeBaseUrl}/GetQuotes",
    }

    fyersBaseUrl = "https://api.fyers.in"
    fyersApi = {
        "profile": f"{fyersBaseUrl}/api/v2/profile",
        "placeOrder": f"{fyersBaseUrl}/api/v2/orders",
        "getQuotes": f"{fyersBaseUrl}/data-rest/v2/quotes/?symbols=",
    }

    angleOneBaseUrl = "https://apiconnect.angelbroking.com"
    angleOneApi = {
        "placeOrder": f"{angleOneBaseUrl}/rest/secure/angelbroking/order/v1/placeOrder",
    }

    # tickDataUrl = "http://139.59.92.18:81/v1/api"
    tickDataUrl = "http://localhost:8080/v1/api"
    tickDataApi = {
        "getCurrentCandleData": f"{tickDataUrl}/websocket/currentCandleData",
        "getCandleData": f"{tickDataUrl}/websocket/candleData",
    }
