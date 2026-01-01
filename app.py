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

    # ユーザー情報を取得して登録（なければ作成）
    try:
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name
    except:
        user_name = "User"

    EconomyService.register_user(user_id, user_name)

    # 現在時刻
    now = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=9))
    )  # 日本時間
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    reply_text = ""

    # --- 1. 勉強開始 ---
    if msg == "勉強開始":
        if GSheetService.log_activity(user_id, user_name, today, current_time):
            reply_text = (
                f"【記録開始】\n{current_time} スタート！\n今日も頑張ってえらい！"
            )
        else:
            reply_text = (
                "エラー：記録に失敗しました。スプレッドシートを確認してください。"
            )

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    # --- 2. 勉強終了 ---
    elif msg == "勉強終了":
        result = GSheetService.update_end_time(user_id, current_time)
        if result:
            # 時間計算
            start_time_str = result["start_time"]
            try:
                start_dt = datetime.datetime.strptime(start_time_str, "%H:%M:%S")
                end_dt = datetime.datetime.strptime(current_time, "%H:%M:%S")

                # 日付またぎ対応（簡易）
                if end_dt < start_dt:
                    end_dt += datetime.timedelta(days=1)

                duration = end_dt - start_dt
                minutes = int(duration.total_seconds() / 60)

                # 報酬計算 (例: 1分 = 1 EXP)
                earned_exp = minutes
                new_balance = EconomyService.add_exp(
                    user_id, earned_exp, "STUDY_REWARD"
                )

                hours, mins = divmod(minutes, 60)
                reply_text = (
                    f"【記録終了】\nお疲れ様でした！\n"
                    f"勉強時間: {hours}時間{mins}分\n"
                    f"獲得EXP: {earned_exp} EXP\n"
                    f"現在残高: {new_balance} EXP"
                )
            except Exception as e:
                print(f"計算エラー: {e}")
                reply_text = "時間の計算に失敗しました。"
        else:
            reply_text = "「勉強開始」が見つかりません。\n先に「勉強開始」を押してね！"

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    # --- 3. ショップメニュー表示 ---
    elif msg == "ショップ" or msg == "使う":
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
