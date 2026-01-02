import datetime
from linebot.models import TextSendMessage, FlexSendMessage
from bot_instance import line_bot_api
from services.economy import EconomyService
from services.approval import ApprovalService
from services.shop import ShopService
from utils.template_loader import load_template


def handle_message(event, text):
    user_id = event.source.user_id

    if text in ["管理", "承認", "admin"]:
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="権限がありません。")
            )
            return True

        pending_items = ApprovalService.get_all_pending()

        if not pending_items:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="現在、承認待ちの項目はありません。"),
            )
            return True

        # カルーセル作成
        carousel = load_template("approval_list.json")
        bubbles = carousel["contents"]

        # ショップアイテムを一度だけ取得（最適化）
        shop_items_cache = None

        for item in pending_items:
            p_type = item["type"]
            data = item["data"]

            if p_type == "study":
                bubble = load_template(
                    "approval_card_study.json",
                    user_name=data["user_name"],
                    date=data["date"],
                    start_time=data["start_time"],
                    end_time=data["end_time"],
                    earned_exp=data.get("earned_exp", 0),
                    row_index=data["row_index"],
                    user_id=data["user_id"],
                )
                if "earned_exp" not in data:
                    try:
                        s = datetime.datetime.strptime(data["start_time"], "%H:%M:%S")
                        e = datetime.datetime.strptime(data["end_time"], "%H:%M:%S")
                        if e < s:
                            e += datetime.timedelta(days=1)
                        mins = int((e - s).total_seconds() / 60)
                        if mins > 90:
                            mins = 90
                        bubble = load_template(
                            "approval_card_study.json",
                            user_name=data["user_name"],
                            date=data["date"],
                            start_time=data["start_time"],
                            end_time=data["end_time"],
                            earned_exp=mins,
                            row_index=data["row_index"],
                            user_id=data["user_id"],
                        )
                    except:
                        pass
                bubbles.append(bubble)

            elif p_type == "job":
                bubble = load_template(
                    "approval_card_job.json",
                    user_name=data["user_name"],
                    job_name=data["job_title"],
                    reward=data["reward"],
                    row_index=data["job_id"],
                    user_id=data["user_id"],
                )
                bubbles.append(bubble)

            elif p_type == "shop":
                if shop_items_cache is None:
                    shop_items_cache = ShopService.get_items()

                item_name = data["item_key"]
                item_info = shop_items_cache.get(data["item_key"])
                if item_info:
                    item_name = item_info["name"]

                bubble = load_template(
                    "approval_card_shop.json",
                    user_name=data["user_name"],
                    item_name=item_name,
                    cost=data["cost"],
                    row_index=data["request_id"],
                    user_id=data["user_id"],
                )
                bubbles.append(bubble)

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="承認待ち一覧", contents=carousel),
        )
        return True

    return False
