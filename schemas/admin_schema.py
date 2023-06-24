
def UserModelShow(item) -> dict:
    return {
        "id": item["_id"],
        "app_id": item["app_id"],
        "name": item["name"],
        "mobile_no": item["mobile_no"],
        "email_id": item["email_id"],
        "role": item["role"],
        "is_live": item["is_live"],
        "is_subscribed": item["is_subscribed"],
        "is_copy_trade": item["is_copy_trade"],
        "referral_code": item["referral_code"],
        "status": item["status"],
    }


def UserModelList(entity) -> list:
    return [UserModelShow(item) for item in entity]


def UserLimited(item) -> dict:
    return {
        "id": item["_id"],
        "app_id": item["app_id"],
        "name": item["name"],
        "mobile_no": item["mobile_no"],
        "email_id": item["email_id"],
    }


def UserLimitedList(entity) -> list:
    return [UserLimited(item) for item in entity]
