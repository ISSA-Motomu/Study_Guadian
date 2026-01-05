from linebot.models import TextSendMessage, FlexSendMessage
from bot_instance import line_bot_api
from services.job import JobService
from services.economy import EconomyService
from utils.template_loader import load_template
from handlers import common
import datetime

# 簡易的な状態管理
user_states = {}


def send_job_list(reply_token, user_id):
    # 1. 自分の担当中タスクを表示
    active_jobs = JobService.get_user_active_jobs(user_id)

    # ベースのテンプレートを読み込み
    job_flex = load_template("job_list.json")
    contents = job_flex["body"]["contents"]

    if active_jobs:
        header = load_template(
            "job_section_header.json", text="🔥 進行中のタスク", color="#ff5555"
        )
        contents.append(header)

        for job in active_jobs:
            deadline_text = job.get("deadline", "")
            if not deadline_text:
                deadline_text = "期限なし"

            row = load_template(
                "job_row_active.json",
                title=job["title"],
                job_id=job["job_id"],
                deadline=deadline_text,
            )
            contents.append(row)

        contents.append({"type": "separator", "margin": "md"})

    # 2. 募集中のタスクを表示
    open_jobs = JobService.get_open_jobs()

    header_open = load_template(
        "job_section_header.json", text="📋 募集中のタスク", color="#333333"
    )
    contents.append(header_open)

    if not open_jobs:
        contents.append(
            {
                "type": "text",
                "text": "今募集してるタスクはないみたい💦",
                "size": "sm",
                "color": "#aaaaaa",
                "margin": "sm",
            }
        )
    else:
        for job in open_jobs:
            deadline_text = job.get("deadline", "")
            if not deadline_text:
                deadline_text = "期限なし"

            row = load_template(
                "job_row_open.json",
                title=job["title"],
                reward=job["reward"],
                job_id=job["job_id"],
                deadline=deadline_text,
            )
            contents.append(row)

    # 3. Admin用メニュー (仕事追加ボタン)
    if EconomyService.is_admin(user_id):
        contents.append({"type": "separator", "margin": "md"})
        # GoogleフォームのURLを設定してください
        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSclo5UBPPyzLBuY1mukZfDOn7wEWt6fLNIdkQVPAL9IZxSTsQ/viewform?usp=header"
        button = load_template("job_create_button.json", form_url=form_url)
        contents.append(button)

    line_bot_api.reply_message(
        reply_token,
        FlexSendMessage(alt_text="お手伝いリスト", contents=job_flex),
    )


def handle_postback(event, action, data):
    line_user_id = event.source.user_id
    user_id = common.get_current_user_id(line_user_id)

    if action == "job_list":
        send_job_list(event.reply_token, user_id)
        return True

    if action == "job_accept":
        # 管理者は受注不可
        if EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="🚫 管理者はお手伝いできないよ💦 子供たちに任せよう！"
                ),
            )
            return True

        job_id = data.get("id")
        success, result = JobService.accept_job(job_id, user_id)

        if success:
            # 完了報告ボタン付きメッセージ
            finish_flex = load_template(
                "job_finish.json", job_title=result, job_id=job_id
            )
            line_bot_api.reply_message(
                event.reply_token,
                FlexSendMessage(alt_text="受注完了", contents=finish_flex),
            )

            # Adminへの通知
            try:
                user_info = EconomyService.get_user_info(user_id)
                user_name = user_info["display_name"] if user_info else "User"

                admins = EconomyService.get_admin_users()
                admin_ids = [u["user_id"] for u in admins if u.get("user_id")]

                if admin_ids:
                    line_bot_api.multicast(
                        admin_ids,
                        TextSendMessage(
                            text=f"🔔 {user_name} が「{result}」を受注しました！"
                        ),
                    )
            except Exception as e:
                print(f"Admin通知エラー: {e}")
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=f"エラー: {result}")
            )
        return True

    elif action == "job_finish":
        job_id = data.get("id")

        # コメント入力待ち状態へ遷移
        user_states[user_id] = {"state": "WAITING_JOB_COMMENT", "job_id": job_id}
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="お疲れ様！\n完了報告のコメント、教えてくれる？"),
        )
        return True

    elif action == "job_reject":
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="権限がありません")
            )
            return True

        job_id = data.get("job_id") or data.get("row_id")
        success, result = JobService.reject_job(job_id)

        # 承認者名を取得
        try:
            approver_profile = line_bot_api.get_profile(user_id)
            approver_name = approver_profile.display_name
        except:
            approver_name = "管理者"

        if success:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"「{result}」を却下しました。（ステータスをASSIGNEDに戻しました）\n担当：{approver_name}"
                ),
            )

            # ユーザーへ通知
            target_id = data.get("target")
            if target_id:
                try:
                    line_bot_api.push_message(
                        target_id,
                        TextSendMessage(
                            text=f"😢 お手伝い「{result}」が却下されちゃった…\n担当：{approver_name}\n内容を確認して、もう一回報告してみて！"
                        ),
                    )
                except:
                    pass
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=f"エラー: {result}")
            )
        return True

    elif action == "job_approve":
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="権限がありません")
            )
            return True

        job_id = data.get("id") or data.get("row_id")
        request_time = data.get("time", "")
        success, result = JobService.approve_job(job_id)

        # 承認者名を取得
        try:
            approver_profile = line_bot_api.get_profile(user_id)
            approver_name = approver_profile.display_name
        except:
            approver_name = "ADMIN"

        if success:
            # 対象者名を取得
            worker_id = result.get("worker_id")
            worker_info = EconomyService.get_user_info(worker_id)
            worker_name = worker_info["display_name"] if worker_info else "ユーザー"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"💮 {worker_name}さんの「{result['title']}」を承認しました。\n(ユーザーへ通知を送信しました)"
                ),
            )

            # 対象ユーザーへ通知
            try:
                msg_text = f"🧹 お手伝い「{result['title']}」が承認されたよ！ありがとう✨\n承認者：{approver_name}\n+{result['reward']} EXP GET！\n(今のEXP: {result['balance']})"
                if request_time:
                    msg_text += f"\n申請時刻：{request_time}"

                line_bot_api.push_message(
                    worker_id,
                    TextSendMessage(text=msg_text),
                )
            except:
                pass
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=f"エラー: {result}")
            )
        return True

    return False


def handle_message(event, text):
    user_id = event.source.user_id

    # 状態チェック
    state_data = user_states.get(user_id)
    if state_data and state_data.get("state") == "WAITING_JOB_COMMENT":
        # コメントを受け取って処理
        comment = text
        job_id = state_data["job_id"]

        # 状態クリア
        del user_states[user_id]

        success, result = JobService.finish_job(job_id, user_id, comment)

        if success:
            # 親への承認依頼
            try:
                user_info = EconomyService.get_user_info(user_id)
                user_name = user_info["display_name"] if user_info else "User"
            except:
                user_name = "User"

            now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            timestamp = now.strftime("%H:%M")

            approve_flex = load_template(
                "job_approve_request.json",
                user_name=user_name,
                job_title=result["title"],
                job_reward=result["reward"],
                job_id=job_id,
                comment=comment,
                timestamp=timestamp,
            )
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(
                        text="お疲れ様！親御さんに報告しておいたよ✨ 承認を待っててね！"
                    ),
                    FlexSendMessage(alt_text="承認依頼", contents=approve_flex),
                ],
            )

            # Adminへの通知 (Multicast)
            try:
                admins = EconomyService.get_admin_users()
                admin_ids = [
                    u["user_id"]
                    for u in admins
                    if u.get("user_id")
                    and not str(u["user_id"]).startswith("U_virtual_")
                ]
                if admin_ids:
                    line_bot_api.multicast(
                        admin_ids,
                        FlexSendMessage(
                            alt_text="お手伝い完了報告", contents=approve_flex
                        ),
                    )
            except Exception as e:
                print(f"Admin通知エラー: {e}")

        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=f"エラー: {result}")
            )
        return True

    if text == "ジョブ" or text == "お手伝い":
        send_job_list(event.reply_token, user_id)
        return True

    return False
