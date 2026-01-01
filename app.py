import os
import datetime
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    FlexSendMessage,
    PostbackEvent,  # ← PostbackEventを追加
)
from dotenv import load_dotenv

from services.gsheet import GSheetService
from services.economy import EconomyService
from services.stats import SagaStats

load_dotenv()

app = Flask(__name__)

# ... (設定部分はそのまま) ...
LINE_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# --- 商品リスト（ハードコードで定義） ---
SHOP_ITEMS = {
    "game_30": {"name": "🎮 ゲーム30分", "cost": 300},
    "game_60": {"name": "🎮 ゲーム1時間", "cost": 600},
    "cash_100": {"name": "💴 お小遣い100円", "cost": 100},
    "snack": {"name": "🍩 おやつ券", "cost": 150},
}


@app.route("/")
def home():
    return "Saga Guardian Active"


@app.route("/callback", methods=["POST"])
def callback():
    # ... (そのまま) ...
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


# ★★★ ここから新機能：ボタン操作の処理 ★★★
@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    # data="action=buy&item=game_30" のような文字列が来るので分解
    data = dict(x.split("=") for x in event.postback.data.split("&"))

    action = data.get("action")

    # --- 1. 商品購入処理 ---
    if action == "buy":
        item_key = data.get("item")
        item = SHOP_ITEMS.get(item_key)

        if not item:
            return

        # 残高チェック
        if EconomyService.check_balance(user_id, item["cost"]):
            # EXP減算 (先払い)
            new_balance = EconomyService.add_exp(
                user_id, -item["cost"], f"BUY_{item_key}"
            )

            # 親への承認リクエストカードを作成
            profile = line_bot_api.get_profile(user_id)

            approval_flex = {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "⚠️ 承認リクエスト",
                            "color": "#ffffff",
                            "weight": "bold",
                        }
                    ],
                    "backgroundColor": "#ff5555",
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"{profile.display_name} からの申請",
                            "weight": "bold",
                        },
                        {
                            "type": "text",
                            "text": f"商品: {item['name']}",
                            "size": "lg",
                            "margin": "md",
                        },
                        {
                            "type": "text",
                            "text": f"消費: {item['cost']} EXP",
                            "color": "#ff5555",
                        },
                        {
                            "type": "text",
                            "text": f"現在残高: {new_balance} EXP",
                            "size": "sm",
                            "color": "#aaaaaa",
                        },
                    ],
                },
                "footer": {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        # 承認ボタン（Adminのみ押せるようにするが、一旦全員押せる仕様で出す）
                        {
                            "type": "button",
                            "action": {
                                "type": "postback",
                                "label": "許可",
                                "data": f"action=approve&target={user_id}&item={item_key}",
                            },
                            "style": "primary",
                        },
                        # 却下ボタン（返金処理用）
                        {
                            "type": "button",
                            "action": {
                                "type": "postback",
                                "label": "却下",
                                "data": f"action=deny&target={user_id}&cost={item['cost']}",
                            },
                            "style": "secondary",
                        },
                    ],
                },
            }

            # 購入者へのメッセージ
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(
                        text=f"✅ {item['name']} を申請しました。\n(残高: {new_balance} EXP)\n親の承認をお待ちください..."
                    ),
                    FlexSendMessage(alt_text="承認リクエスト", contents=approval_flex),
                ],
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="🚫 EXPが足りません！もっと勉強しよう。"),
            )

    # --- 2. 承認処理 (親が押す) ---
    elif action == "approve":
        # ★ここを追加：セキュリティチェック
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="🚫 あなたには承認権限がありません。\nお母さんに頼んでね！"
                ),
            )
            return

        # 権限があれば実行
        target_id = data.get("target")
        item_key = data.get("item")
        item = SHOP_ITEMS.get(item_key)

        # 弟への通知（本来は push_message ですが、無料版LINE Botの制限があるため reply で返すか、
        # あるいはグループLINE内でのやり取りなら reply で全員に見えます）
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"🙆‍♀️ 承認されました！\n\n🎟 【利用許可証】\n{item['name']}\n\nこの画面を親に見せて使いましょう！"
            ),
        )

    # --- 3. 却下処理 (親が押す -> 返金) ---
    elif action == "deny":
        # 却下も管理者のみ可能にする
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="🚫 権限がありません。")
            )
            return

        target_id = data.get("target")
        cost = int(data.get("cost"))

        # 返金処理
        EconomyService.add_exp(target_id, cost, "REFUND")

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"🙅‍♀️ 却下されました。\n{cost} EXP を返金しました。ドンマイ！"
            ),
        )


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    user_id = event.source.user_id

    # ユーザー登録等はそのまま
    EconomyService.register_user(user_id, "User")

    # ... (勉強開始・終了のロジックはそのまま維持) ...
    # (ここに以前の勉強開始・終了コードが入っています)

    # ★★★ ショップメニュー表示 ★★★
    if msg == "ショップ" or msg == "使う":
        # 商品カタログFlex Messageを作成
        items_contents = []
        for key, item in SHOP_ITEMS.items():
            row = {
                "type": "box",
                "layout": "horizontal",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": item["name"],
                        "flex": 3,
                        "gravity": "center",
                    },
                    {
                        "type": "text",
                        "text": f"{item['cost']} EXP",
                        "flex": 1,
                        "align": "end",
                        "gravity": "center",
                        "color": "#27ACB2",
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "postback",
                            "label": "購入",
                            "data": f"action=buy&item={key}",
                        },
                        "style": "primary",
                        "flex": 2,
                    },
                ],
            }
            items_contents.append(row)

        shop_flex = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "🛒 EXPショップ",
                        "weight": "bold",
                        "size": "xl",
                    }
                ],
            },
            "body": {"type": "box", "layout": "vertical", "contents": items_contents},
        }

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="ショップメニュー", contents=shop_flex),
        )

    # ... (ランキングなどの他のコマンド) ...
