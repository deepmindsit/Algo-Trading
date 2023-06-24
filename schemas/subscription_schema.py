
def PlanModelShow(item) -> dict:
    return {
        "id": item["_id"],
        "plan_name": item["plan_name"],
        "price": item["price"],
        "period_in_days": item["period_in_days"],
        "offer": item["offer"],
        "offer_start_date": item["offer_start_date"],
        "offer_end_date": item["offer_end_date"],
        "description": item["description"],
        "status": item["status"],
    }


def PlanModelList(entity) -> list:
    return [PlanModelShow(item) for item in entity]


def SubscriptionModelShow(item) -> dict:
    return {
        "id": item["_id"],
        "user_id": item["user_id"],
        "plan_id": item["plan_id"],
        "from_date": item["from_date"],
        "to_date": item["to_date"],
        "status": item["status"],
        "plan": item['plan'],
    }


def SubscriptionModelList(entity) -> list:
    return [SubscriptionModelShow(item) for item in entity]
