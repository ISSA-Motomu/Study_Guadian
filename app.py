import os
from flask import Flask, request, abort, render_template
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    PostbackEvent,
)
from dotenv import load_dotenv

# 新しい構成のインポート
from bot_instance import line_bot_api, handler
from handlers import study, shop, job, admin, status, common, help
from services.history import HistoryService
from services.economy import EconomyService

load_dotenv()

app = Flask(__name__, template_folder="templates/html")


@app.route("/")
def home():
    return "Saga Guardian Active"


@app.route("/admin/dashboard")
def admin_dashboard():
    # 本来は認証が必要だが、簡易的にURLを知っている人のみアクセス可能とする
    # もしくはクエリパラメータで ?key=secret_key のように簡易認証を入れても良い

    transactions = HistoryService.get_all_transactions()

    # ユーザーIDを名前に変換
    users = EconomyService.get_all_users()
    user_map = {str(u["user_id"]): u["display_name"] for u in users}

    for tx in transactions:
        uid = str(tx.get("user_id"))
        tx["user_name"] = user_map.get(uid, uid[:4])

    return render_template("admin_dashboard.html", transactions=transactions)


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(PostbackEvent)
def handle_postback(event):
    # data="action=buy&item=game_30" のような文字列が来るので分解
    data = dict(x.split("=") for x in event.postback.data.split("&"))
    action = data.get("action")

    # 各ハンドラに委譲
    if study.handle_postback(event, action, data):
        return
    if shop.handle_postback(event, action, data):
        return
    if job.handle_postback(event, action, data):
        return

    # どのハンドラも処理しなかった場合
    print(f"Unhandled Postback: {action}")


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text

    # 共通処理（ユーザー登録など）
    common.handle_message(event, msg)

    # 各ハンドラに委譲
    if help.handle_message(event, msg):
        return
    if study.handle_message(event, msg):
        return
    if shop.handle_message(event, msg):
        return
    if job.handle_message(event, msg):
        return
    if admin.handle_message(event, msg):
        return
    if status.handle_message(event, msg):
        return

    # どのハンドラも処理しなかった場合
    # 必要であれば「わかりません」などを返す
    pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
