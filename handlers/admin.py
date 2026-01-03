import datetime
import traceback
from linebot.models import TextSendMessage, FlexSendMessage
from bot_instance import line_bot_api
from services.economy import EconomyService
from services.approval import ApprovalService
from services.shop import ShopService
from services.job import JobService
from utils.template_loader import load_template


# 管理者の操作状態を保持する辞書
# Key: admin_user_id, Value: {"state": "WAITING_...", "data": {...}}
admin_states = {}


def handle_postback(event, action, data):
    """管理機能のPostback処理"""
    user_id = event.source.user_id

    # 管理者チェック
    if not EconomyService.is_admin(user_id):
        return False

    if action == "admin_give_exp":
        target_user_id = data.get("target_id")
        amount = int(data.get("amount"))

        admin_states[user_id] = {
            "state": "WAITING_REASON",
            "target_user_id": target_user_id,
            "amount": amount,
        }

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"ユーザーへの付与ポイント: {amount}pt\n付与する理由を入力してください。\n(例: お手伝い、テスト満点、臨時ボーナス)"
            ),
        )
        return True

    elif action == "admin_give_exp_custom":
        target_user_id = data.get("target_id")

        admin_states[user_id] = {
            "state": "WAITING_AMOUNT",
            "target_user_id": target_user_id,
        }

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="付与するポイント数を入力してください。(半角数字)"),
        )
        return True

    return False


def handle_message(event, text):
    try:
        user_id = event.source.user_id

        # 状態チェック (ポイント付与フロー中かどうか)
        if user_id in admin_states:
            state_data = admin_states[user_id]
            state = state_data.get("state")

            if state == "WAITING_AMOUNT":
                try:
                    amount = int(text)
                    state_data["amount"] = amount
                    state_data["state"] = "WAITING_REASON"
                    admin_states[user_id] = state_data  # 更新

                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(
                            text=f"ユーザーへの付与ポイント: {amount}pt\n付与する理由を入力してください。"
                        ),
                    )
                    return True
                except ValueError:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(
                            text="ポイント数は半角数字で入力してください。"
                        ),
                    )
                    return True

            elif state == "WAITING_REASON":
                reason = text
                target_user_id = state_data.get("target_user_id")
                amount = state_data.get("amount")

                # 実行
                # related_id に理由を含める
                EconomyService.add_exp(
                    target_user_id, amount, related_id=f"ADMIN_GRANT:{reason}"
                )

                # 状態クリア
                del admin_states[user_id]

                # ユーザー名取得（表示用）
                user_info = EconomyService.get_user_info(target_user_id)
                user_name = (
                    user_info["display_name"] if user_info else str(target_user_id)
                )

                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text=f"✅ ポイント付与完了\n対象: {user_name}\n金額: {amount}pt\n理由: {reason}"
                    ),
                )
                return True

        if text.startswith("タスク追加"):
            if not EconomyService.is_admin(user_id):
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text="権限がありません。")
                )
                return True

            # Parse args: タスク追加 [Title] [Reward]
            parts = text.split()
            if len(parts) < 3:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="使用法: タスク追加 [タイトル] [報酬]"),
                )
                return True

            # 最後の要素を報酬、それ以外をタイトルとする（タイトルにスペースが含まれる場合に対応）
            try:
                reward = int(parts[-1])
                title = " ".join(parts[1:-1])
            except ValueError:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="報酬は数値で指定してください。"),
                )
                return True

            success, result = JobService.create_job(title, reward, "", user_id)
            if success:
                msg = f"タスク「{title}」を作成しました。(報酬: {reward})"
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

                # Notify Users
                all_users = EconomyService.get_all_users()
                target_ids = [
                    str(u["user_id"]) for u in all_users if str(u["user_id"]) != user_id
                ]

                if target_ids:
                    try:
                        line_bot_api.multicast(
                            target_ids,
                            TextSendMessage(
                                text=f"🆕 新しいお手伝いが追加されました！\n\n「{title}」\n報酬: {reward} EXP\n\n早い者勝ちだよ！"
                            ),
                        )
                    except Exception as e:
                        print(f"Multicast Error: {e}")
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f"作成失敗: {result}")
                )
            return True

        if text == "商品追加":
            # Google Form for Item Addition
            form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfFxXNFm-xuB4LMbn8Y6ePX4y46Rl0C34ouTzi7qYYuSSOXWg/viewform"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"商品追加はこちらのフォームから行ってください：\n{form_url}"
                ),
            )
            return True

        if text == "ポイント付与":
            if not EconomyService.is_admin(user_id):
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text="権限がありません。")
                )
                return True

            # ユーザー選択用のカルーセルを表示
            users = EconomyService.get_all_users()
            # 自分以外を表示
            targets = [u for u in users if str(u["user_id"]) != user_id]

            if not targets:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text="対象ユーザーがいません。")
                )
                return True

            bubbles = []
            for u in targets:
                bubbles.append(
                    {
                        "type": "bubble",
                        "body": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": u["display_name"],
                                    "weight": "bold",
                                    "size": "xl",
                                },
                                {
                                    "type": "text",
                                    "text": f"現在のEXP: {u['current_exp']}",
                                    "size": "sm",
                                    "color": "#aaaaaa",
                                },
                            ],
                        },
                        "footer": {
                            "type": "box",
                            "layout": "vertical",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "button",
                                    "style": "primary",
                                    "action": {
                                        "type": "postback",
                                        "label": "100 EXP",
                                        "data": f"action=admin_give_exp&target={u['user_id']}&amount=100",
                                    },
                                },
                                {
                                    "type": "button",
                                    "style": "secondary",
                                    "action": {
                                        "type": "postback",
                                        "label": "500 EXP",
                                        "data": f"action=admin_give_exp&target={u['user_id']}&amount=500",
                                    },
                                },
                                {
                                    "type": "button",
                                    "style": "link",
                                    "action": {
                                        "type": "postback",
                                        "label": "カスタム入力",
                                        "data": f"action=admin_give_exp_custom&target={u['user_id']}",
                                    },
                                },
                            ],
                        },
                    }
                )

            line_bot_api.reply_message(
                event.reply_token,
                FlexSendMessage(
                    alt_text="ポイント付与対象選択",
                    contents={"type": "carousel", "contents": bubbles},
                ),
            )
            return True

        if text in ["管理", "承認", "admin", "メニュー"]:
            if not EconomyService.is_admin(user_id):
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text="権限がありません。")
                )
                return True

            # 管理メニューを表示
            menu_bubble = load_template("admin_menu.json")
            if menu_bubble:
                line_bot_api.reply_message(
                    event.reply_token,
                    FlexSendMessage(alt_text="管理メニュー", contents=menu_bubble),
                )
            return True

        if text == "承認確認":
            if not EconomyService.is_admin(user_id):
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
            if not carousel:
                print("Error: approval_list.json could not be loaded.")
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="テンプレート読み込みエラーが発生しました。"),
                )
                return True

            bubbles = carousel["contents"]

            # ショップアイテムを一度だけ取得（最適化）
            shop_items_cache = None

            for item in pending_items:
                p_type = item["type"]
                data = item["data"]

                # 必須項目のサニタイズ (空文字だとLINE APIエラーになるため)
                user_name = data.get("user_name")
                if not user_name:
                    user_name = str(data.get("user_id", "Unknown"))
                if not user_name:
                    user_name = "Unknown"

                if p_type == "study":
                    bubble = load_template(
                        "approval_card_study.json",
                        user_name=user_name,
                        date=data.get("date", ""),
                        start_time=data.get("start_time", ""),
                        end_time=data.get("end_time", ""),
                        earned_exp=data.get("earned_exp", 0),
                        row_index=data["row_index"],
                        user_id=data["user_id"],
                    )
                    if "earned_exp" not in data:
                        try:
                            s = datetime.datetime.strptime(
                                data["start_time"], "%H:%M:%S"
                            )
                            e = datetime.datetime.strptime(data["end_time"], "%H:%M:%S")
                            if e < s:
                                e += datetime.timedelta(days=1)
                            mins = int((e - s).total_seconds() / 60)
                            if mins > 90:
                                mins = 90
                            bubble = load_template(
                                "approval_card_study.json",
                                user_name=user_name,
                                date=data.get("date", ""),
                                start_time=data.get("start_time", ""),
                                end_time=data.get("end_time", ""),
                                earned_exp=mins,
                                row_index=data["row_index"],
                                user_id=data["user_id"],
                            )
                        except:
                            pass
                    if bubble:
                        bubbles.append(bubble)

                elif p_type == "job":
                    job_title = data.get("job_title")
                    if not job_title:
                        job_title = "無題のタスク"

                    bubble = load_template(
                        "approval_card_job.json",
                        user_name=user_name,
                        job_name=job_title,
                        reward=data["reward"],
                        row_index=data["job_id"],
                        user_id=data["user_id"],
                    )
                    if bubble:
                        bubbles.append(bubble)

                elif p_type == "shop":
                    if shop_items_cache is None:
                        shop_items_cache = ShopService.get_items()

                    item_name = data.get("item_key", "商品")
                    item_info = shop_items_cache.get(data["item_key"])
                    if item_info:
                        item_name = item_info["name"]

                    if not item_name:
                        item_name = "商品"

                    bubble = load_template(
                        "approval_card_shop.json",
                        user_name=user_name,
                        item_name=item_name,
                        cost=data["cost"],
                        row_index=data["request_id"],
                        user_id=data["user_id"],
                    )
                    if bubble:
                        bubbles.append(bubble)

            line_bot_api.reply_message(
                event.reply_token,
                FlexSendMessage(alt_text="承認待ち一覧", contents=carousel),
            )
            return True

    except Exception as e:
        print(f"Admin Handler Error: {e}")
        traceback.print_exc()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="管理機能でエラーが発生しました。ログを確認してください。"
            ),
        )
        return True

    return False
