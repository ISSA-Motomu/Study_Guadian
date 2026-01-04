from linebot.models import TextSendMessage, FlexSendMessage
from bot_instance import line_bot_api
from services.economy import EconomyService
from utils.template_loader import load_template
import random

# 簡易的な状態管理
user_states = {}

# ユーザーセッション管理 (LINE User ID -> App User ID)
# { "U_line_id": "U_app_user_id" }
ACTIVE_SESSIONS = {}


def get_current_user_id(line_user_id):
    """現在の操作ユーザーIDを取得（なりすまし対応）"""
    return ACTIVE_SESSIONS.get(line_user_id, line_user_id)


def switch_user(line_user_id, target_user_id):
    """操作ユーザーを切り替え"""
    ACTIVE_SESSIONS[line_user_id] = target_user_id


def handle_postback(event, action, data):
    line_user_id = event.source.user_id

    if action == "switch_user_menu":
        # ユーザー切り替えメニューを表示
        users = EconomyService.get_all_users()

        bubbles = []
        for u in users:
            uid = str(u.get("user_id"))
            name = u.get("display_name")
            role = u.get("role")

            # ADMINユーザーはリストに表示しない（切り替え不可）
            if role == "ADMIN":
                continue

            # 現在選択中のユーザーかどうか
            current_uid = get_current_user_id(line_user_id)
            is_active = uid == current_uid

            bg_color = "#E0F7FA" if is_active else "#FFFFFF"
            status_text = "選択中" if is_active else "切替"
            status_color = "#00BCD4" if is_active else "#aaaaaa"

            bubble = {
                "type": "bubble",
                "size": "micro",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": bg_color,
                    "contents": [
                        {
                            "type": "text",
                            "text": name,
                            "weight": "bold",
                            "size": "sm",
                            "wrap": True,
                        },
                        {
                            "type": "text",
                            "text": f"Role: {role}",
                            "size": "xxs",
                            "color": "#aaaaaa",
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
                                "label": status_text,
                                "data": f"action=do_switch_user&target={uid}",
                            },
                            "style": "secondary" if is_active else "primary",
                            "height": "sm",
                            "color": status_color if is_active else None,
                        }
                    ],
                },
            }
            bubbles.append(bubble)

        # 新規ユーザー作成ボタン
        add_user_bubble = {
            "type": "bubble",
            "size": "micro",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "＋ 新規追加",
                        "weight": "bold",
                        "size": "sm",
                        "align": "center",
                        "color": "#444444",
                    },
                    {
                        "type": "text",
                        "text": "LINEなしユーザー",
                        "size": "xxs",
                        "color": "#aaaaaa",
                        "align": "center",
                    },
                ],
                "justifyContent": "center",
                "height": "60px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "postback",
                            "label": "作成",
                            "data": "action=create_new_user_flow",
                        },
                        "height": "sm",
                    }
                ],
            },
        }
        bubbles.append(add_user_bubble)

        carousel = {"type": "carousel", "contents": bubbles}

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="ユーザー切替", contents=carousel),
        )
        return True

    elif action == "do_switch_user":
        target_uid = data.get("target")
        user_info = EconomyService.get_user_info(target_uid)
        name = user_info.get("display_name") if user_info else target_uid

        switch_user(line_user_id, target_uid)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"ユーザーを「{name}」に切り替えました。"),
        )
        return True

    elif action == "create_new_user_flow":
        # 新規ユーザー作成フロー開始
        user_states[line_user_id] = "WAITING_NEW_USER_NAME"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="新しく追加するユーザーの名前を入力してください。"),
        )
        return True

    return False


def handle_message(event, text):
    line_user_id = event.source.user_id

    # 新規ユーザー作成フロー
    state = user_states.get(line_user_id)
    if state == "WAITING_NEW_USER_NAME":
        new_name = text.strip()
        if len(new_name) > 10:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="名前が長すぎます。10文字以内で入力してください。"
                ),
            )
            return True

        # 仮想ID生成 (U_virtual_timestamp)
        import time

        virtual_id = f"U_virtual_{int(time.time())}_{random.randint(100, 999)}"

        if EconomyService.register_user(virtual_id, new_name):
            EconomyService.add_exp(virtual_id, 500, "WELCOME_BONUS")

            # 自動的に切り替え
            switch_user(line_user_id, virtual_id)

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"ユーザー「{new_name}」を作成し、切り替えました！"
                ),
            )
            if line_user_id in user_states:
                del user_states[line_user_id]
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="作成に失敗しました。")
            )
        return True

    # --- 以下、既存ロジック ---

    # 現在の操作ユーザーIDを取得
    user_id = get_current_user_id(line_user_id)

    # 既存ユーザーかチェック
    # (毎回APIを叩くのはコストが高いが、現状のアーキテクチャでは許容)
    user_info = EconomyService.get_user_info(user_id)

    # --- 開発用: 権限変更コマンド ---
    # 通常のユーザーには見えない隠しコマンド
    if text == "デバッグモード有効":
        if EconomyService.update_user_role(user_id, "ADMIN"):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="🔧 管理者権限(ADMIN)を付与しました。\n「コマンド」と入力すると管理メニューが見れます。"
                ),
            )
            return True
    elif text == "デバッグモード無効":
        if EconomyService.update_user_role(user_id, "USER"):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="🔧 管理者権限を解除し、一般ユーザー(USER)に戻りました。"
                ),
            )
            return True
    # ------------------------------

    if user_info:
        # 既に登録済みなら何もしない（他のハンドラへ）
        return False

    # --- 未登録ユーザーのオンボーディング処理 ---
    # ここに来るのは「LINE IDそのもの」が未登録の場合のみ
    # (仮想ユーザーに切り替えている場合は user_info があるはずなのでここには来ない)

    state = user_states.get(line_user_id)

    if state == "WAITING_NAME":
        # 名前入力待ち
        display_name = text.strip()

        # 「ヘルプ」などのコマンドが入力された場合は、名前として登録せずにスルーする
        # (ユーザーが間違ってコマンドを打った場合や、システムが誤認した場合の対策)
        if display_name in ["ヘルプ", "help", "使い方", "説明", "コマンド", "管理"]:
            # 状態をリセットしてFalseを返すことで、後続のヘルプハンドラなどに処理を委譲する
            # ただし、未登録状態なのでヘルプハンドラ側でどう扱うかは注意が必要
            # ここでは「名前入力待ち」を維持しつつ、ヘルプを表示させるためにFalseを返す
            return False

        if len(display_name) > 10:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="名前が長すぎます。10文字以内で入力してください。"
                ),
            )
            return True

        # 登録処理 (LINE IDで登録)
        if EconomyService.register_user(line_user_id, display_name):
            # 初回ボーナス付与
            EconomyService.add_exp(line_user_id, 500, "WELCOME_BONUS")

            welcome_flex = load_template("welcome_success.json", name=display_name)
            if welcome_flex:
                line_bot_api.reply_message(
                    event.reply_token,
                    FlexSendMessage(alt_text="登録完了", contents=welcome_flex),
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text=f"ようこそ、{display_name}さん！\n登録完了ボーナスとして 500 pt をプレゼントしました！"
                    ),
                )

            # 状態クリア
            if line_user_id in user_states:
                del user_states[line_user_id]
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="登録に失敗しました。もう一度お試しください。"),
            )
        return True

    else:
        # 初回接触（または未登録状態での発言）
        user_states[line_user_id] = "WAITING_NAME"

        onboarding_flex = load_template("welcome_onboarding.json")
        if onboarding_flex:
            line_bot_api.reply_message(
                event.reply_token,
                FlexSendMessage(alt_text="GAME START", contents=onboarding_flex),
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="はじめまして！Study Guardianへようこそ。\n\nまずはあなたの名前を教えてね。\n（呼び名をメッセージで送ってください）"
                ),
            )
        return True
