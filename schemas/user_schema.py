

def userModelLoginRes(item) -> dict:
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
        "referral_link": item["referral_link"],
        "login_token": item["login_token"],
        "token": item["token"],
        "status": item["status"],
    }
