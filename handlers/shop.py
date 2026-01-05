from linebot.models import TextSendMessage, FlexSendMessage
from bot_instance import line_bot_api
from services.shop import ShopService
from services.economy import EconomyService
from utils.template_loader import load_template
from handlers import common
import datetime

# 簡易的な状態管理
user_states = {}


def handle_postback(event, action, data):
    line_user_id = event.source.user_id
    user_id = common.get_current_user_id(line_user_id)

    if action == "buy":
        item_key = data.get("item")
        shop_items = ShopService.get_items()
        item = shop_items.get(item_key)

        if not item:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="あれ？そのアイテム、見つからないみたい💦"),
            )
            return True

        confirm_flex = load_template(
            "buy_confirm.json",
            item_name=item["name"],
            item_cost=item["cost"],
            item_key=item_key,
        )
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="交換確認", contents=confirm_flex),
        )
        return True

    elif action == "confirm_buy":
        item_key = data.get("item")
        shop_items = ShopService.get_items()
        item = shop_items.get(item_key)

        if not item:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="あれ？そのアイテム、見つからないみたい💦"),
            )
            return True

        # 残高チェック
        if EconomyService.check_balance(user_id, item["cost"]):
            # コメント入力待ち状態へ遷移
            user_states[user_id] = {
                "state": "WAITING_SHOP_COMMENT",
                "item_key": item_key,
                "cost": item["cost"],
                "item_name": item["name"],
            }
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"「{item['name']}」だね！\n何に使うの？一言教えて！"
                ),
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="🚫 ポイントが足りないみたい💦 もっと勉強して貯めよう！"
                ),
            )
        return True

    elif action == "approve":
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="🚫 承認権限がないよ💦 お母さんに頼んでみてね！"),
            )
            return True

        target_id = data.get("target")
        item_key = data.get("item")
        shop_items = ShopService.get_items()
        item = shop_items.get(item_key)

        item_name = item["name"] if item else "アイテム"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"🙆‍♀️ 承認されたよ！\n\n🎟 【利用許可証】\n{item_name}\n\nこの画面を親御さんに見せて使ってね！"
            ),
        )
        return True

    elif action == "deny":
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="🚫 権限がありません。")
            )
            return True

        target_id = data.get("target")
        cost = int(data.get("cost"))

        # 返金処理
        EconomyService.add_exp(target_id, cost, "REFUND")

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"🙅‍♀️ 却下されちゃった…\n{cost} pt は返金しておいたよ。ドンマイ！"
            ),
        )
        return True

    elif action == "shop_reject":
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="権限がありません")
            )
            return True

        target_id = data.get("target")
        row_id = data.get("request_id") or data.get("row_id")
        cost = int(data.get("cost", 0))

        # 承認者名を取得
        try:
            approver_profile = line_bot_api.get_profile(user_id)
            approver_name = approver_profile.display_name
        except:
            approver_name = "ADMIN"

        denied_item_key = ShopService.deny_request(row_id)
        if denied_item_key:
            # 商品名を取得
            shop_items = ShopService.get_items()
            item_info = shop_items.get(denied_item_key)
            item_name = item_info["name"] if item_info else "商品"

            # Refund
            EconomyService.add_exp(target_id, cost, "REFUND")

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"交換リクエストを却下しました。\n{cost} pt を返金しました。\n担当：{approver_name}"
                ),
            )

            # ユーザーへ通知
            try:
                line_bot_api.push_message(
                    target_id,
                    TextSendMessage(
                        text=f"🙅‍♀️ 交換リクエストが却下されちゃった…\n申請アイテム：{item_name}\n担当：{approver_name}\n{cost} pt は返金しておいたよ。ドンマイ！"
                    ),
                )
            except:
                pass
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="却下に失敗しました。")
            )
        return True

    elif action == "shop_approve":
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="権限がありません")
            )
            return True

        target_id = data.get("target")
        cost = int(data.get("cost"))
        row_id = data.get("row_id")
        request_time = data.get("time", "")

        # 承認者名を取得
        try:
            approver_profile = line_bot_api.get_profile(user_id)
            approver_name = approver_profile.display_name
        except:
            approver_name = "ADMIN"

        # 対象者名を取得
        target_user_info = EconomyService.get_user_info(target_id)
        target_name = (
            target_user_info["display_name"] if target_user_info else "ユーザー"
        )

        # 既に購入時にEXPは引かれているので、ここではステータス更新のみ
        approved_item_key = ShopService.approve_request(row_id)
        if approved_item_key:
            # 商品名を取得
            shop_items = ShopService.get_items()
            item_info = shop_items.get(approved_item_key)
            item_name = item_info["name"] if item_info else "商品"

            # 現在の残高を取得
            user_info = EconomyService.get_user_info(target_id)
            new_balance = user_info.get("current_exp", 0) if user_info else 0

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"{target_name}さんの「{item_name}」を承認しました。\n(ユーザーへ通知を送信しました)"
                ),
            )

            # ユーザーへ通知
            try:
                msg_text = f"🛍️ ポイント交換リクエスト「{item_name}」が承認されたよ！やったね✨\n承認者：{approver_name}\n(今の残高: {new_balance} pt)\n\n親御さんに見せて使ってね！"
                if request_time:
                    msg_text += f"\n申請時刻：{request_time}"

                line_bot_api.push_message(
                    target_id,
                    TextSendMessage(text=msg_text),
                )
            except:
                pass
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"エラー：リクエストが見つからないか、既に処理されています。"
                ),
            )
        return True

    return False


def handle_message(event, text):
    user_id = event.source.user_id

    # 状態チェック
    state_data = user_states.get(user_id)
    if state_data and state_data.get("state") == "WAITING_SHOP_COMMENT":
        # コメントを受け取って処理
        comment = text
        item_key = state_data["item_key"]
        cost = state_data["cost"]
        item_name = state_data["item_name"]

        # 状態クリア
        del user_states[user_id]

        # EXP減算 (先払い)
        new_balance = EconomyService.add_exp(user_id, -cost, f"BUY_{item_key}")

        # 購入リクエストを記録 (Admin承認用)
        ShopService.create_request(user_id, item_key, cost, comment)

        # 親への承認リクエストカードを作成
        user_info = EconomyService.get_user_info(user_id)
        user_name = user_info.get("display_name", "Unknown") if user_info else "Unknown"

        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        timestamp = now.strftime("%H:%M")

        approval_flex = load_template(
            "approval_request.json",
            user_name=user_name,
            item_name=item_name,
            item_cost=cost,
            new_balance=new_balance,
            user_id=user_id,
            item_key=item_key,
            comment=comment,
            timestamp=timestamp,
        )

        # 管理者(親)に通知を送る
        admins = EconomyService.get_admin_users()
        admin_notified = False
        for admin in admins:
            admin_uid = str(admin.get("user_id"))
            if not admin_uid.startswith("U_virtual_"):
                try:
                    line_bot_api.push_message(
                        admin_uid,
                        FlexSendMessage(
                            alt_text="承認リクエスト", contents=approval_flex
                        ),
                    )
                    admin_notified = True
                except Exception as e:
                    print(f"Push Error to {admin_uid}: {e}")

        # 購入者へのメッセージ
        reply_msgs = [
            TextSendMessage(
                text=f"[ポイント交換申請]\n✅ {item_name} を申請したよ！\n(残高: {new_balance} pt)\n親御さんの承認を待っててね！"
            )
        ]

        if not admin_notified:
            reply_msgs.append(
                TextSendMessage(
                    text="※管理者が見つからないため、通知されませんでした。"
                )
            )

        line_bot_api.reply_message(event.reply_token, reply_msgs)
        return True

    if text in ["ショップ", "使う", "ポイント交換"]:
        shop_items = ShopService.get_items()
        if not shop_items:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="今は交換できる商品がないみたい💦"),
            )
            return True

        # 【松】カルーセル形式（カード型）
        bubbles = []
        for key, item in shop_items.items():
            # 説明文がない場合は空文字
            desc = item.get("description", " ")
            if not desc:
                desc = " "

            bubble = {
                "type": "bubble",
                "size": "micro",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#eeeeee",
                    "contents": [
                        {
                            "type": "text",
                            "text": "ITEM",
                            "color": "#aaaaaa",
                            "size": "xxs",
                            "weight": "bold",
                        }
                    ],
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": item["name"],
                            "weight": "bold",
                            "size": "sm",
                            "wrap": True,
                        },
                        {
                            "type": "text",
                            "text": f"{item['cost']} EXP",
                            "weight": "bold",
                            "size": "md",
                            "color": "#ff8800",
                            "margin": "md",
                        },
                        {
                            "type": "text",
                            "text": desc,
                            "size": "xxs",
                            "color": "#aaaaaa",
                            "wrap": True,
                            "margin": "xs",
                        },
                    ],
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "action": {
                                "type": "postback",
                                "label": "購入",
                                "data": f"action=buy&item={key}",
                            },
                            "style": "primary",
                            "height": "sm",
                        }
                    ],
                },
            }
            bubbles.append(bubble)

        # LINEの制限対応: カルーセルは最大12個まで
        # 12個を超える場合は複数のメッセージに分割して送信する (最大5通まで = 60個)
        reply_messages = []
        chunk_size = 12

        for i in range(0, len(bubbles), chunk_size):
            chunk = bubbles[i : i + chunk_size]
            shop_flex = {"type": "carousel", "contents": chunk}
            reply_messages.append(
                FlexSendMessage(alt_text="ポイント交換", contents=shop_flex)
            )
            if len(reply_messages) >= 5:
                break

        line_bot_api.reply_message(event.reply_token, reply_messages)
        return True

    return False
