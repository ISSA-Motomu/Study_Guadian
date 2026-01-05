from linebot.models import TextSendMessage, FlexSendMessage, PostbackAction
from bot_instance import line_bot_api
from services.mission import MissionService
from services.economy import EconomyService
from handlers import common


def handle_message(event, text):
    if text == "ミッション":
        user_id = common.get_current_user_id(event.source.user_id)
        missions = MissionService.get_active_missions(user_id)

        if not missions:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="今挑戦できるミッションはないみたい💦"),
            )
            return True

        # Create Carousel
        bubbles = []
        for m in missions:
            bubbles.append(
                {
                    "type": "bubble",
                    "header": {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#673AB7",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📜 ミッション",
                                "color": "#ffffff",
                                "weight": "bold",
                                "size": "sm",
                            }
                        ],
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": m["title"],
                                "weight": "bold",
                                "size": "xl",
                                "wrap": True,
                            },
                            {
                                "type": "text",
                                "text": m["description"],
                                "size": "sm",
                                "color": "#666666",
                                "wrap": True,
                                "margin": "md",
                            },
                            {"type": "separator", "margin": "lg"},
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "margin": "md",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "報酬:",
                                        "size": "sm",
                                        "color": "#aaaaaa",
                                    },
                                    {
                                        "type": "text",
                                        "text": f"{m['reward']} pt",
                                        "size": "lg",
                                        "color": "#ff5555",
                                        "weight": "bold",
                                        "align": "end",
                                    },
                                ],
                            },
                        ],
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "action": {
                                    "type": "postback",
                                    "label": "完了報告",
                                    "data": f"action=mission_complete&id={m['mission_id']}",
                                },
                            }
                        ],
                    },
                }
            )

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(
                alt_text="ミッション一覧",
                contents={"type": "carousel", "contents": bubbles},
            ),
        )
        return True
    return False


def handle_postback(event, action, data):
    line_user_id = event.source.user_id
    user_id = common.get_current_user_id(line_user_id)

    if action == "mission_complete":
        mission_id = data.get("id")
        if MissionService.complete_mission(mission_id, user_id):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="ミッション完了！報告しておいたよ✨\n親御さんの承認を待っててね！"
                ),
            )

            # Notify Admin
            # 管理者全員に通知
            admins = EconomyService.get_admins()
            user_info = EconomyService.get_user_info(user_id)
            user_name = user_info["display_name"] if user_info else "ユーザー"

            for admin in admins:
                try:
                    line_bot_api.push_message(
                        admin["user_id"],
                        TextSendMessage(
                            text=f"📜 {user_name}さんがミッションを完了しました！\n承認待ちリストを確認してください。"
                        ),
                    )
                except:
                    pass
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="あれ？ミッションが見つからないか、もう報告済みみたい💦"
                ),
            )
        return True

    elif action == "mission_approve":
        # Admin approval logic is handled in admin.py?
        # No, approval logic is usually in the handler that deals with the resource type.
        # But `admin.py` handles the "Approve" button click from the approval list.
        # The approval list is generated in `admin.py` using `ApprovalService`.
        # `ApprovalService` needs to be updated to include missions.
        # And `admin.py` needs to handle `mission_approve`.
        pass

    return False
