from linebot.models import FlexSendMessage
from bot_instance import line_bot_api
from utils.template_loader import load_template


def handle_message(event, text):
    if text in ["ヘルプ", "help", "使い方", "説明書", "manual"]:
        manual_flex = load_template("manual_carousel.json")
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="使い方ガイド", contents=manual_flex),
        )
        return True
    return False
