from linebot.models import TextSendMessage, FlexSendMessage
from bot_instance import line_bot_api
from services.shop import ShopService
from services.economy import EconomyService
from utils.template_loader import load_template
from handlers import common


def handle_postback(event, action, data):
    line_user_id = event.source.user_id
    user_id = common.get_current_user_id(line_user_id)

    if action == "buy":
        item_key = data.get("item")
        shop_items = ShopService.get_items()
        item = shop_items.get(item_key)

        if not item:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="アイテムが見つかりません。")
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
                event.reply_token, TextSendMessage(text="アイテムが見つかりません。")
            )
            return True

        # 残高チェック
        if EconomyService.check_balance(user_id, item["cost"]):
            # EXP減算 (先払い)
            new_balance = EconomyService.add_exp(
                user_id, -item["cost"], f"BUY_{item_key}"
            )

            # 購入リクエストを記録 (Admin承認用)
            ShopService.create_request(user_id, item_key, item["cost"])

            # 親への承認リクエストカードを作成
            profile = line_bot_api.get_profile(user_id)

            approval_flex = load_template(
                "approval_request.json",
                user_name=profile.display_name,
                item_name=item["name"],
                item_cost=item["cost"],
                new_balance=new_balance,
                user_id=user_id,
                item_key=item_key,
            )

            # 購入者へのメッセージ
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(
                        text=f"[ポイント交換申請]\n✅ {item['name']} を申請しました。\n(残高: {new_balance} pt)\n親の承認をお待ちください..."
                    ),
                    FlexSendMessage(alt_text="承認リクエスト", contents=approval_flex),
                ],
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="🚫 ポイントが足りません！もっと勉強しよう。"),
            )
        return True

    elif action == "approve":
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="🚫 あなたには承認権限がありません。\nお母さんに頼んでね！"
                ),
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
                text=f"🙆‍♀️ 承認されました！\n\n🎟 【利用許可証】\n{item_name}\n\nこの画面を親に見せて使いましょう！"
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
                text=f"🙅‍♀️ 却下されました。\n{cost} pt を返金しました。ドンマイ！"
            ),
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

        # 承認者名を取得
        try:
            approver_profile = line_bot_api.get_profile(user_id)
            approver_name = approver_profile.display_name
        except:
            approver_name = "管理者"

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
                    text=f"{target_name}さんの「{item_name}」を承認しました！\n承認者：{approver_name}\n\n(ポイントは交換申請時に消費済みです)"
                ),
            )

            # ユーザーへ通知
            try:
                line_bot_api.push_message(
                    target_id,
                    TextSendMessage(
                        text=f"🛍️ ポイント交換リクエスト「{item_name}」が承認されました！\n(現在残高: {new_balance} pt)\n\n親に見せて使ってね！"
                    ),
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
    if text in ["ショップ", "使う", "ポイント交換"]:
        shop_items = ShopService.get_items()
        if not shop_items:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="現在販売中の商品はありません。"),
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

        shop_flex = {"type": "carousel", "contents": bubbles}

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="ポイント交換", contents=shop_flex),
        )
        return True

    return False
