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
from handlers import study, shop, job, admin, status, common, help, gacha
from services.history import HistoryService
from services.economy import EconomyService
from utils.debouncer import Debouncer

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

    # 詳細情報解決用のマップ
    job_map = JobService.get_all_jobs_map()
    shop_items = ShopService.get_items()

    for tx in transactions:
        uid = str(tx.get("user_id"))
        tx["user_name"] = user_map.get(uid, uid[:4])

        # 取引内容の解決
        rtype = tx.get("tx_type")
        rid = str(tx.get("related_id", ""))

        desc = rid
        if rtype == "REWARD":
            if rid == "STUDY_REWARD":
                desc = "✏️ 勉強報酬"
            elif rid.startswith("JOB_"):
                jid = rid.replace("JOB_", "")
                jtitle = job_map.get(jid, "不明なタスク")
                desc = f"🧹 {jtitle}"
        elif rtype == "SPEND":
            if rid.startswith("BUY_"):
                ikey = rid.replace("BUY_", "")
                iname = shop_items.get(ikey, {}).get("name", ikey)
                desc = f"🛒 {iname}"
        elif rtype == "REFUND":
            desc = "↩️ 返金"

        tx["description"] = desc

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
    user_id = event.source.user_id
    data_str = event.postback.data

    # 連打防止 (5秒間)
    if Debouncer.is_locked(user_id, data_str):
        return

    # data="action=buy&item=game_30" のような文字列が来るので分解
    data = dict(x.split("=") for x in data_str.split("&"))
    action = data.get("action")

    # 各ハンドラに委譲
    if study.handle_postback(event, action, data):
        return
    if shop.handle_postback(event, action, data):
        return
    if admin.handle_postback(event, action, data):
        return
    if job.handle_postback(event, action, data):
        return

    # どのハンドラも処理しなかった場合
    print(f"Unhandled Postback: {action}")


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text

    # 共通処理（ユーザー登録・オンボーディング）
    if common.handle_message(event, msg):
        return

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
    if gacha.handle_message(event, msg):
        return

    # どのハンドラも処理しなかった場合
    # 必要であれば「わかりません」などを返す
    pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
