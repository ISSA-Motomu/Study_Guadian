from linebot.models import TextSendMessage, FlexSendMessage
from bot_instance import line_bot_api
from services.job import JobService
from services.economy import EconomyService
from utils.template_loader import load_template
from handlers import common


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
            row = load_template(
                "job_row_active.json", title=job["title"], job_id=job["job_id"]
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
                "text": "現在募集中のタスクはありません",
                "size": "sm",
                "color": "#aaaaaa",
                "margin": "sm",
            }
        )
    else:
        for job in open_jobs:
            row = load_template(
                "job_row_open.json",
                title=job["title"],
                reward=job["reward"],
                job_id=job["job_id"],
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
                    text="🚫 管理者はお手伝いを受注できません。\n子供たちに任せましょう！"
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
        success, result = JobService.finish_job(job_id, user_id)

        if success:
            # 親への承認依頼
            try:
                user_info = EconomyService.get_user_info(user_id)
                user_name = user_info["display_name"] if user_info else "User"
            except:
                user_name = "User"

            approve_flex = load_template(
                "job_approve_request.json",
                user_name=user_name,
                job_title=result["title"],
                job_reward=result["reward"],
                job_id=job_id,
            )
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(
                        text="お疲れ様！親に報告しました。承認を待ってね。"
                    ),
                    FlexSendMessage(alt_text="承認依頼", contents=approve_flex),
                ],
            )
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
        success, result = JobService.approve_job(job_id)

        # 承認者名を取得
        try:
            approver_profile = line_bot_api.get_profile(user_id)
            approver_name = approver_profile.display_name
        except:
            approver_name = "管理者"

        if success:
            # 対象者名を取得
            worker_id = result.get("worker_id")
            worker_info = EconomyService.get_user_info(worker_id)
            worker_name = worker_info["display_name"] if worker_info else "ユーザー"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"💮 {worker_name}さんの「{result['title']}」を承認しました！\n承認者：{approver_name}\n\n報酬 {result['reward']} EXP を付与しました。\n(現在残高: {result['balance']} EXP)"
                ),
            )
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=f"エラー: {result}")
            )
        return True

    return False


def handle_message(event, text):
    user_id = event.source.user_id

    if text == "ジョブ" or text == "お手伝い":
        send_job_list(event.reply_token, user_id)
        return True

    return False
