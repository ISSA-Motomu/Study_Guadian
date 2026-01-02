import datetime
from linebot.models import (
    TextSendMessage,
    FlexSendMessage,
    QuickReply,
    QuickReplyButton,
    MessageAction,
)
from bot_instance import line_bot_api
from services.gsheet import GSheetService
from services.economy import EconomyService
from services.stats import SagaStats
from utils.template_loader import load_template

# 簡易的な状態管理 (メモリ上)
user_states = {}


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

        subject = data.get("subject", "")

        if GSheetService.log_activity(user_id, user_name, today, current_time, subject):
            subject_text = f"【{subject}】" if subject else ""
            reply_text = f"【記録開始】\n{current_time} {subject_text}スタート！\n今日も頑張ってえらい！"
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

                # ランク計算と保存 (Looker Studio用)
                stats = SagaStats.calculate(minutes)
                if stats:
                    GSheetService.update_study_stats(
                        result["row_index"], minutes, stats["rank"]
                    )

                # 状態を保存して、成果報告を促す
                user_states[user_id] = {
                    "state": "WAITING_COMMENT",
                    "row_index": result["row_index"],
                    "minutes": minutes,
                }

                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="【記録終了】\nお疲れ様でした！\n\n今日の成果を一言で教えてね。\n(例: 算数ドリル P20-22, 英単語50個)"
                    ),
                )

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

        # 承認者名を取得
        try:
            approver_profile = line_bot_api.get_profile(user_id)
            approver_name = approver_profile.display_name
        except:
            approver_name = "管理者"

        # 対象者名を取得
        target_user_info = EconomyService.get_user_info(target_id)
        target_name = (
            target_user_info["display_name"] if target_user_info else "ユーザー"
        )

        # 1. シートのステータスを更新
        if row_id and GSheetService.approve_study(int(row_id)):
            # 2. EXP付与 (承認成功時のみ)
            new_balance = EconomyService.add_exp(target_id, minutes, "STUDY_REWARD")

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"{target_name}さんの勉強時間を承認しました！\n承認者：{approver_name}\n\n{minutes} EXP を付与しました。"
                ),
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
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="エラー：既に承認されているか、処理に失敗しました。"
                ),
            )
        return True

    return False


def handle_message(event, text):
    user_id = event.source.user_id

    # 状態チェック
    state_data = user_states.get(user_id)
    if state_data:
        state = state_data.get("state")

        if state == "WAITING_COMMENT":
            # コメントを受け取り、集中度を聞く
            user_states[user_id]["comment"] = text
            user_states[user_id]["state"] = "WAITING_CONCENTRATION"

            # クイックリプライ作成
            items = [
                QuickReplyButton(action=MessageAction(label="5 (最高)", text="5")),
                QuickReplyButton(action=MessageAction(label="4 (良い)", text="4")),
                QuickReplyButton(action=MessageAction(label="3 (普通)", text="3")),
                QuickReplyButton(action=MessageAction(label="2 (微妙)", text="2")),
                QuickReplyButton(action=MessageAction(label="1 (ダメ)", text="1")),
            ]

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="今日の集中度はどうでしたか？",
                    quick_reply=QuickReply(items=items),
                ),
            )
            return True

        elif state == "WAITING_CONCENTRATION":
            # 集中度を受け取り、完了処理へ
            if text in ["1", "2", "3", "4", "5"]:
                concentration = int(text)
                finalize_study(event, user_id, state_data, concentration)
                # 状態クリア
                del user_states[user_id]
                return True
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="1〜5の数字で答えてね。"),
                )
                return True

    if text == "勉強開始":
        # 教科選択ダイアログを表示
        subject_flex = load_template("study_subject_select.json")
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="教科選択", contents=subject_flex),
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


def finalize_study(event, user_id, state_data, concentration):
    row_index = state_data["row_index"]
    minutes = state_data["minutes"]
    comment = state_data.get("comment", "なし")

    # 詳細情報を保存
    GSheetService.update_study_details(row_index, comment, concentration)

    hours, mins = divmod(minutes, 60)
    earned_exp = minutes

    # ユーザーへの返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text=f"記録しました！\n勉強時間: {hours}時間{mins}分\n成果: {comment}\n集中度: {concentration}/5\n\n親に承認依頼を送りました。"
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
                comment=comment,
                concentration=concentration,
            )
            line_bot_api.multicast(
                admin_ids,
                FlexSendMessage(alt_text="勉強完了報告", contents=approve_flex),
            )
    except Exception as e:
        print(f"Admin通知エラー: {e}")
