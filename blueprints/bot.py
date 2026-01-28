from flask import Blueprint, request, abort
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, PostbackEvent
from bot_instance import handler
from utils.debouncer import Debouncer

# Handlers imply logic registration on import
from handlers import study, shop, job, admin, status, common, help, gacha, mission

bot_bp = Blueprint("bot", __name__)


@bot_bp.route("/callback", methods=["POST"])
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

    # グループ判定
    is_group = event.source.type != "user"

    # 各ハンドラに委譲
    if common.handle_postback(event, action, data):
        return
    if study.handle_postback(event, action, data):
        return
    if shop.handle_postback(event, action, data):
        return

    # グループでは管理機能を使えないようにする
    if not is_group:
        if admin.handle_postback(event, action, data):
            return

    if job.handle_postback(event, action, data):
        return
    if mission.handle_postback(event, action, data):
        return
    if status.handle_postback(event, action, data):
        return

    # どのハンドラも処理しなかった場合
    print(f"Unhandled Postback: {action}")


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    user_id = event.source.user_id

    # 連打防止 (メッセージも3秒間ロック)
    if Debouncer.is_locked(user_id, msg):
        return

    # グループ判定
    is_group = event.source.type != "user"

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
    if mission.handle_message(event, msg):
        return

    # グループでは管理機能を使えないようにする
    if not is_group:
        if admin.handle_message(event, msg):
            return

    if status.handle_message(event, msg):
        return
    if gacha.handle_message(event, msg):
        return

    # どのハンドラも処理しなかった場合
    pass
