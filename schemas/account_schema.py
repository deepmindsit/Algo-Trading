
def AccountModelShow(item) -> dict:
    return {
        "id": item["_id"],
        "broker": item["broker"],
        "client_id": item["client_id"],
        "api_key": item["api_key"],
        "api_secret": item["api_secret"],
        "token_generated_at": item["token_generated_at"],
        "trade_status": item["trade_status"],
        "paper_trade": item["paper_trade"],
        "margin": item["margin"],
        "status": item["status"],
    }


def AccountModelList(entity) -> list:
    return [AccountModelShow(item) for item in entity]
