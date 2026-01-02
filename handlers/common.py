from linebot.models import TextSendMessage
from bot_instance import line_bot_api
from services.economy import EconomyService

# 簡易的な状態管理
user_states = {}


def handle_message(event, text):
    user_id = event.source.user_id

    # 既存ユーザーかチェック
    # (毎回APIを叩くのはコストが高いが、現状のアーキテクチャでは許容)
    user_info = EconomyService.get_user_info(user_id)

    if user_info:
        # 既に登録済みなら何もしない（他のハンドラへ）
        return False

    # --- 未登録ユーザーのオンボーディング処理 ---
    state = user_states.get(user_id)

    if state == "WAITING_NAME":
        # 名前入力待ち
        display_name = text.strip()
        if len(display_name) > 10:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="名前が長すぎます。10文字以内で入力してください。"
                ),
            )
            return True

        # 登録処理
        if EconomyService.register_user(user_id, display_name):
            # 初回ボーナス付与
            EconomyService.add_exp(user_id, 500, "WELCOME_BONUS")

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"ようこそ、{display_name}さん！\n登録完了ボーナスとして 500 EXP をプレゼントしました！\n\nまずは「ヘルプ」と入力して使い方を見てみてね。"
                ),
            )
            # 状態クリア
            if user_id in user_states:
                del user_states[user_id]
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="登録に失敗しました。もう一度お試しください。"),
            )
        return True

    else:
        # 初回接触（または未登録状態での発言）
        user_states[user_id] = "WAITING_NAME"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="はじめまして！Study Guardianへようこそ。\n\nまずはあなたの名前を教えてね。\n（呼び名をメッセージで送ってください）"
            ),
        )
        return True
