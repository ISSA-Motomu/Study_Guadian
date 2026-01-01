import os
import datetime
from services.economy import EconomyService
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv

# 自作モジュールのインポート
from services.gsheet import GSheetService
from services.stats import SagaStats

load_dotenv()

app = Flask(__name__)

LINE_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)


@app.route("/")
def home():
    return "Saga Guardian System Active"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    user_name = profile.display_name

    # ★ここに追加：ユーザー登録チェック（銀行口座開設）
    # 毎回チェックするのは非効率に見えますが、
    # GSpreadのAPI制限にかからない程度なら、確実性を取ってこの位置でOK
    EconomyService.register_user(user_id, user_name)

    # 自分の情報を取得（権限チェックや残高表示のため）
    user_info = EconomyService.get_user_info(user_id)
    
    # 時刻取得
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

    # 時刻取得
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    reply_text = ""

    if msg == "勉強開始":
        success = GSheetService.log_activity(user_id, user_name, today, current_time)
        if success:
            reply_text = f"【記録開始】\n{current_time} スタート！\n今日も未来のために稼ぎましょう。"
        else:
            reply_text = "エラー：データベース接続に失敗しました。"

    elif msg == "勉強終了":
        result = GSheetService.update_end_time(user_id, current_time)

        if result:
            # 時間計算
            start_dt = datetime.datetime.strptime(result["start_time"], "%H:%M:%S")
            end_dt = datetime.datetime.strptime(current_time, "%H:%M:%S")
            duration = end_dt - start_dt
            total_minutes = int(duration.total_seconds() / 60)
            hours, minutes = divmod(total_minutes, 60)

            # 統計計算
            stats = SagaStats.calculate(total_minutes)
            ex_point = total_minutes  # 仮：1分1円

            reply_text = (
                f"【記録終了】\n⏱ {hours}時間{minutes}分\n💰 獲得: {ex_point} EXP\n\n"
            )
            if stats:
                reply_text += f"📊 佐賀県中1シミュレーション\n"
                reply_text += f"┣ 偏差値: {stats['deviation']}\n"
                reply_text += f"┣ 推定順位: {stats['rank']}位\n"
                reply_text += f"┗ 💨 {stats['overtaken']}人抜き！"
        else:
            reply_text = "「勉強開始」ボタンが押されていません。"

    else:
        # 今は無視、あるいはメニューへの誘導
        pass

    if reply_text:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))


if __name__ == "__main__":
    app.run()
