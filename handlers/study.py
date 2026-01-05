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
from services.history import HistoryService
from services.status_service import StatusService
from utils.template_loader import load_template
from handlers import common
from utils.achievements import AchievementManager, ACHIEVEMENT_MASTER

# 簡易的な状態管理 (メモリ上)
user_states = {}

SUBJECT_COLORS = {
    "国語": "#FF6B6B",
    "数学": "#4D96FF",
    "英語": "#FFD93D",
    "理科": "#6BCB77",
    "社会": "#9D4EDD",
    "その他": "#95A5A6",
}


def handle_postback(event, action, data):
    line_user_id = event.source.user_id
    user_id = common.get_current_user_id(line_user_id)

    if action == "start_study":
        try:
            # ユーザー名解決 (なりすまし対応)
            user_info = EconomyService.get_user_info(user_id)
            user_name = user_info["display_name"] if user_info else "User"
        except:
            user_name = "User"

        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        subject = data.get("subject", "")

        if GSheetService.log_activity(user_id, user_name, today, current_time, subject):
            # Flex Message for Study Session
            color = SUBJECT_COLORS.get(subject, "#27ACB2")
            bubble = load_template(
                "study_session.json",
                subject=subject,
                start_time=current_time,
                color=color,
            )

            line_bot_api.reply_message(
                event.reply_token,
                FlexSendMessage(alt_text="勉強中...", contents=bubble),
            )
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="エラー：記録に失敗しました。")
            )
        return True

    elif action == "confirm_cancel_study":
        confirm_flex = load_template(
            "confirm_dialog.json",
            text="本当に勉強記録を取り消しますか？",
            action_data="action=cancel_study",
        )
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="取消確認", contents=confirm_flex),
        )
        return True

    elif action == "cancel_study":
        if GSheetService.cancel_study(user_id):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="勉強記録を取り消しました。"),
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="取り消し可能な記録が見つかりませんでした。"),
            )
        return True

    elif action == "pause_study":
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        current_time = now.strftime("%H:%M:%S")

        # End current session temporarily
        result = GSheetService.update_end_time(user_id, current_time)
        if result:
            # Calculate duration just for display (optional)
            # We don't need to do full stats update here, but we should probably log duration
            # update_end_time sets status to PENDING.
            # We will leave it as PENDING. The parent will see multiple entries.

            # Calculate minutes for stats
            start_time_str = result["start_time"]
            try:
                start_dt = datetime.datetime.strptime(start_time_str, "%H:%M:%S")
                end_dt = datetime.datetime.strptime(current_time, "%H:%M:%S")
                if end_dt < start_dt:
                    end_dt += datetime.timedelta(days=1)
                duration = end_dt - start_dt
                minutes = int(duration.total_seconds() / 60)

                # Update stats (Duration/Rank) so it's not empty in sheet
                stats = SagaStats.calculate(minutes)
                if stats:
                    GSheetService.update_study_stats(
                        result["row_index"], minutes, stats["rank"]
                    )
            except:
                pass

            subject = result.get("subject", "")
            bubble = load_template("study_resume.json", subject=subject)
            line_bot_api.reply_message(
                event.reply_token, FlexSendMessage(alt_text="一時中断", contents=bubble)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="あれ？勉強中の記録が見つからないよ？"),
            )
        return True

    elif action == "resume_study":
        # Same as start_study but maybe different message?
        # Let's reuse start_study logic but with "Resumed" text if needed.
        # For simplicity, we just call the same logic as start_study
        # But we need subject from data.

        try:
            user_info = EconomyService.get_user_info(user_id)
            user_name = user_info["display_name"] if user_info else "User"
        except:
            user_name = "User"

        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        subject = data.get("subject", "")

        if GSheetService.log_activity(user_id, user_name, today, current_time, subject):
            color = SUBJECT_COLORS.get(subject, "#27ACB2")
            bubble = load_template(
                "study_session.json",
                subject=subject,
                start_time=current_time,
                color=color,
            )

            # Change text slightly? No, template is fixed.
            # We can just send it.
            line_bot_api.reply_message(
                event.reply_token, FlexSendMessage(alt_text="勉強再開", contents=bubble)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ごめん、再開できなかったみたい💦"),
            )
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
                    "subject": result.get("subject", ""),
                    "start_time": start_time_str,  # 実績判定用に開始時間を保存
                }

                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="【記録終了】\nお疲れ様！頑張ったね✨\n\n今日の成果、一言で教えてくれる？\n(例: 算数ドリル P20-22, 英単語50個)"
                    ),
                )

            except Exception as e:
                print(f"計算エラー: {e}")
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="ごめん、時間の計算がうまくいかなかったみたい💦"
                    ),
                )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="あれ？「勉強開始」の記録が見つからないよ？"),
            )
        return True

    elif action == "study_reject":
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="権限がありません")
            )
            return True

        target_id = data.get("target")
        row_id = data.get("row_id")

        # 承認者名を取得
        try:
            approver_profile = line_bot_api.get_profile(user_id)
            approver_name = approver_profile.display_name
        except:
            approver_name = "管理者"

        if row_id and GSheetService.reject_study(int(row_id)):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"勉強記録を却下しました。\n担当：{approver_name}"
                ),
            )

            # ユーザーへ通知
            try:
                line_bot_api.push_message(
                    target_id,
                    TextSendMessage(
                        text=f"😢 ごめんね、勉強記録が却下されちゃったみたい。\n担当：{approver_name}\n内容を確認して、もう一回申請してみて！"
                    ),
                )
            except:
                pass
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="却下に失敗しました。")
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
        exp = int(data.get("exp", minutes))
        row_id = data.get("row_id")
        request_time = data.get("time", "")

        # 承認者名を取得
        try:
            approver_profile = line_bot_api.get_profile(user_id)
            approver_name = approver_profile.display_name
        except:
            approver_name = "ADMIN"

        # 対象者名を取得
        target_user_info = EconomyService.get_user_info(target_id)
        target_name = (
            target_user_info["display_name"] if target_user_info else "ユーザー"
        )

        # ランクアップ判定のための事前情報取得
        old_stats = HistoryService.get_user_study_stats(target_id)
        old_total = old_stats["total"]
        old_rank_info = StatusService.get_rank_info(old_total)

        # 1. シートのステータスを更新
        if row_id and GSheetService.approve_study(int(row_id)):
            # 2. EXP付与 (承認成功時のみ)
            new_balance = EconomyService.add_exp(target_id, exp, "STUDY_REWARD")

            # ランクアップ判定
            new_total = old_total + minutes
            new_rank_info = StatusService.get_rank_info(new_total)
            is_rank_up = new_rank_info["name"] != old_rank_info["name"]

            # ランクをユーザーシートに保存
            rank_letter = (
                new_rank_info["name"].split(":")[0].replace("Rank ", "").strip()
            )
            EconomyService.update_user_rank(target_id, rank_letter)

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"{target_name}さんの勉強時間を承認しました。\n(ユーザーへ通知を送信しました)"
                ),
            )

            # 対象ユーザーへ通知（Push Message）
            try:
                messages = []
                msg_text = f"💮 勉強時間が承認されたよ！やったね✨\n承認者：{approver_name}\n+{exp} EXP GET！\n(今のEXP: {new_balance})"
                if request_time:
                    msg_text += f"\n申請時刻：{request_time}"

                messages.append(TextSendMessage(text=msg_text))

                if is_rank_up:
                    # ランクアップ通知
                    import os
                    from linebot.models import ImageSendMessage

                    app_url = os.environ.get(
                        "APP_URL", "https://your-app.herokuapp.com"
                    )
                    if app_url.endswith("/"):
                        app_url = app_url[:-1]
                    img_url = f"{app_url}/static/medals/{new_rank_info['img']}"

                    messages.append(
                        TextSendMessage(
                            text=f"🎉 すごい！ランクアップだよ！✨\n新しいランク: {new_rank_info['name']}\nこれからも一緒に頑張ろうね！"
                        )
                    )
                    messages.append(
                        ImageSendMessage(
                            original_content_url=img_url, preview_image_url=img_url
                        )
                    )

                line_bot_api.push_message(target_id, messages)
            except Exception as e:
                print(f"Pushエラー: {e}")
                # 仮想ユーザーIDの場合、Pushは失敗するが、それは仕様として許容する
                # (LINE IDではないため)
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
                    text="今日の集中度、どうだった？こっそり教えて！",
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
                    TextSendMessage(text="1〜5の数字で教えてね！"),
                )
                return True

    if text == "勉強開始":
        # 教科選択ダイアログを表示

        # Check for daily bonus opportunity
        study_count = HistoryService.get_today_study_count(user_id)
        if study_count == 0:
            header_msg = "🔥 今日の5分ボーナス(30pt)未獲得！"
            header_color = "#FF6B6B"
        else:
            header_msg = "科目ごとの色を確認してね！"
            header_color = "#aaaaaa"

        subject_flex = load_template(
            "study_subject_select.json",
            header_message=header_msg,
            header_color=header_color,
        )
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
    subject = state_data.get("subject", "")
    comment = state_data.get("comment", "なし")

    # 詳細情報を保存
    GSheetService.update_study_details(row_index, comment, concentration)

    hours, mins = divmod(minutes, 60)
    earned_exp = minutes

    # デイリーボーナス判定
    bonus_msg = ""
    is_first_today = HistoryService.is_first_study_today(user_id)
    if minutes >= 5 and is_first_today:
        bonus = 30
        earned_exp += bonus
        bonus_msg = f"\n🎁 初回ボーナス: +{bonus}pt"

    # --- 実績判定 (Achievement) ---
    achievement_msg = ""
    try:
        user_info = EconomyService.get_user_info(user_id)
        if user_info:
            # セッション情報
            current_session = {
                "start_time": state_data.get("start_time", ""),
                "minutes": minutes,
                "is_first_ever": int(user_info.get("total_study_time", 0))
                == 0,  # 簡易判定
            }

            new_achievements = AchievementManager.check_achievements(
                user_info, current_session
            )

            if new_achievements:
                # DB更新
                current_str = str(user_info.get("unlocked_achievements", ""))
                new_ids = [a.value for a in new_achievements]

                # 重複排除しつつ結合
                current_set = set(current_str.split(",")) if current_str else set()
                for nid in new_ids:
                    current_set.add(nid)

                updated_str = ",".join(list(current_set))
                EconomyService.update_user_achievements(user_id, updated_str)

                # メッセージ生成
                ach_titles = [ACHIEVEMENT_MASTER[a].title for a in new_achievements]
                achievement_msg = f"\n\n🎉 実績解除！\n" + "\n".join(
                    [f"・{t}" for t in ach_titles]
                )
    except Exception as e:
        print(f"Achievement Error: {e}")
    # ------------------------------

    subject_str = f"\n教科: {subject}" if subject else ""

    # 統計情報の再計算（表示用）
    stats = SagaStats.calculate(minutes)
    stats_msg = ""
    if stats:
        stats_msg = f"\n\n📊 佐賀県統計モデル\n偏差値: {stats['deviation']}\n判定: {stats['school_level']}"
        if stats["is_saganishi"]:
            stats_msg += "\n🌸 佐賀西合格圏内！"

    # ユーザーへの返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text=f"OK！記録したよ✨\n勉強時間: {hours}時間{mins}分{subject_str}\n成果: {comment}\n集中度: {concentration}/5{bonus_msg}{achievement_msg}{stats_msg}\n\n親御さんに報告しておいたからね！"
        ),
    )

    # Adminへの通知
    try:
        user_info = EconomyService.get_user_info(user_id)
        user_name = user_info["display_name"] if user_info else "User"

        admins = EconomyService.get_admin_users()
        admin_ids = [u["user_id"] for u in admins if u.get("user_id")]

        if admin_ids:
            now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            timestamp = now.strftime("%H:%M")

            approve_flex = load_template(
                "study_approve_request.json",
                user_name=user_name,
                hours=hours,
                mins=mins,
                minutes=minutes,
                earned_exp=earned_exp,
                user_id=user_id,
                comment=comment + bonus_msg,
                concentration=concentration,
                timestamp=timestamp,
            )
            line_bot_api.multicast(
                admin_ids,
                FlexSendMessage(alt_text="勉強完了報告", contents=approve_flex),
            )
    except Exception as e:
        print(f"Admin通知エラー: {e}")


def process_timeout_sessions(sessions):
    """タイムアウトしたセッションの事後処理（通知＆状態更新）"""
    for session in sessions:
        user_id = session["user_id"]
        minutes = session["minutes"]
        row_index = session["row_index"]
        subject = session["subject"]
        start_time = session["start_time"]

        # ランク計算と保存
        stats = SagaStats.calculate(minutes)
        if stats:
            GSheetService.update_study_stats(row_index, minutes, stats["rank"])

        # 状態を保存して、成果報告を促す
        user_states[user_id] = {
            "state": "WAITING_COMMENT",
            "row_index": row_index,
            "minutes": minutes,
            "subject": subject,
            "start_time": start_time,
        }

        # 通知送信
        try:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(
                    text=f"⏰ 1時間半経ったよ！根詰めすぎは良くないから、一旦休憩しよ？\n自動で終了にしておくね。\n\n今日の成果、教えてくれる？"
                ),
            )
        except Exception as e:
            print(f"Push Error: {e}")
