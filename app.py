import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

app = Flask(__name__)

# 環境変数から鍵を取り出す
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
YOUR_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

if YOUR_CHANNEL_ACCESS_TOKEN is None or YOUR_CHANNEL_SECRET is None:
    print("【エラー】トークンが見つかりません。.envを確認してください！")

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

@app.route("/")
def hello_world():
    return "Hello! Saga Guardian is running!"

@app.route("/callback", methods=['POST'])
def callback():
    # LINEからのアクセスか確認する署名
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# メッセージが来たら動く部分
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 送られてきたメッセージをそのまま返す（オウム返し）
    received_text = event.message.text
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"あなたは言いました: {received_text}")
    )

if __name__ == "__main__":
    app.run()