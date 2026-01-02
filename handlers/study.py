import datetime
from linebot.models import TextSendMessage, FlexSendMessage
from bot_instance import line_bot_api
from services.gsheet import GSheetService
from services.economy import EconomyService
from utils.template_loader import load_template


def handle_postback(event, action, data):
    user_id = event.source.user_id

    if action == "start_study":
        try:
            profile = line_bot_api.get_profile(user_id)
            user_name = profile.display_name
        except:
            user_name = "User"

        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        if GSheetService.log_activity(user_id, user_name, today, current_time):
            reply_text = (
                f"【記録開始】\n{current_time} スタート！\n今日も頑張ってえらい！"
            )
        else:
            reply_text = "エラー：記録に失敗しました。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return True

    elif action == "end_study":
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        current_time = now.strftime("%H:%M:%S")

        result = GSheetService.update_end_time(user_id, current_time)
        if result:
            start_time_str = result["start_time"]
            try:
                start_dt = datetime.datetime.strptime(start_time_str, "%H:%M:%S")
                end_dt = datetime.datetime.strptime(current_time, "%H:%M:%S")
                if end_dt < start_dt:
                    end_dt += datetime.timedelta(days=1)

                duration = end_dt - start_dt
                minutes = int(duration.total_seconds() / 60)

                # 最大90分(1時間30分)に制限
                if minutes > 90:
                    minutes = 90

                earned_exp = minutes
                hours, mins = divmod(minutes, 60)

                # ユーザーへの返信
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text=f"【記録終了】\nお疲れ様でした！\n勉強時間: {hours}時間{mins}分\n獲得予定EXP: {earned_exp} EXP\n\n親に承認依頼を送りました。承認されるまで待ってね！"
                    ),
                )

                # Adminへの通知
                try:
                    profile = line_bot_api.get_profile(user_id)
                    user_name = profile.display_name
                    admins = EconomyService.get_admin_users()
                    admin_ids = [u["user_id"] for u in admins if u.get("user_id")]

                    if admin_ids:
                        approve_flex = load_template(
                            "study_approve_request.json",
                            user_name=user_name,
                            hours=hours,
                            mins=mins,
                            earned_exp=earned_exp,
                            user_id=user_id,
                        )
                        line_bot_api.multicast(
                            admin_ids,
                            FlexSendMessage(
                                alt_text="勉強完了報告", contents=approve_flex
                            ),
                        )
                except Exception as e:
                    print(f"Admin通知エラー: {e}")

            except Exception as e:
                print(f"計算エラー: {e}")
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="時間の計算に失敗しました。"),
                )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="「勉強開始」が見つかりません。"),
            )
        return True

    elif action == "study_approve":
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="権限がありません")
            )
            return True

        target_id = data.get("target")
        minutes = int(data.get("minutes"))
        row_id = data.get("row_id")

        # 1. シートのステータスを更新
        if row_id:
            GSheetService.approve_study(int(row_id))

        # 2. EXP付与
        new_balance = EconomyService.add_exp(target_id, minutes, "STUDY_REWARD")

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"承認しました！\n{minutes} EXP を付与しました。"),
        )

        # 対象ユーザーへ通知（Push Message）
        try:
            line_bot_api.push_message(
                target_id,
                TextSendMessage(
                    text=f"💮 勉強時間が承認されました！\n+{minutes} EXP\n(現在残高: {new_balance} EXP)"
                ),
            )
        except Exception as e:
            print(f"Pushエラー: {e}")
        return True

    return False


def handle_message(event, text):
    if text == "勉強開始":
        confirm_flex = load_template(
            "confirm_dialog.json",
            text="勉強を始めますか？",
            action_data="action=start_study",
        )
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="勉強開始確認", contents=confirm_flex),
        )
        return True

    elif text == "勉強終了":
        confirm_flex = load_template(
            "confirm_dialog.json",
            text="勉強を終わりますか？",
            action_data="action=end_study",
        )
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="勉強終了確認", contents=confirm_flex),
        )
        return True

    return False
