from linebot.models import TextSendMessage, FlexSendMessage
from bot_instance import line_bot_api
from services.job import JobService
from services.economy import EconomyService
from utils.template_loader import load_template


def handle_postback(event, action, data):
    user_id = event.source.user_id

    if action == "job_accept":
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
                profile = line_bot_api.get_profile(user_id)
                user_name = profile.display_name
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
            profile = line_bot_api.get_profile(user_id)
            approve_flex = load_template(
                "job_approve_request.json",
                user_name=profile.display_name,
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

        job_id = data.get("id")
        success, result = JobService.approve_job(job_id)

        if success:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"💮 承認しました！\n{result['title']} の報酬 {result['reward']} EXP を付与しました。\n(現在残高: {result['balance']} EXP)"
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
            event.reply_token,
            FlexSendMessage(alt_text="お手伝いリスト", contents=job_flex),
        )
        return True

    return False
