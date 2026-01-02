from linebot.models import TextSendMessage, FlexSendMessage
from bot_instance import line_bot_api
from services.economy import EconomyService
from services.history import HistoryService
from utils.template_loader import load_template


def handle_message(event, text):
    user_id = event.source.user_id

    if text in ["状況", "ステータス", "status"]:
        # 1. Adminかどうかチェック
        if EconomyService.is_admin(user_id):
            # --- Admin View (Transaction History) ---
            history = HistoryService.get_admin_history(limit=5)  # LINE上は直近5件だけ

            bubble = load_template("status_admin_view.json")
            # body -> contents[2] is the list container
            list_container = bubble["body"]["contents"][2]["contents"]

            if not history:
                list_container.append(
                    {
                        "type": "text",
                        "text": "履歴なし",
                        "size": "sm",
                        "color": "#aaaaaa",
                    }
                )
            else:
                for tx in history:
                    # tx: tx_id, user_id, amount, tx_type, related_id, timestamp
                    amount = int(tx.get("amount", 0))
                    color = "#ff5555" if amount > 0 else "#5555ff"
                    amount_str = f"+{amount}" if amount > 0 else str(amount)

                    # ユーザー名解決 (簡易的)
                    user_info = EconomyService.get_user_info(str(tx.get("user_id")))
                    user_name = (
                        user_info["display_name"]
                        if user_info
                        else str(tx.get("user_id"))[:4]
                    )

                    row = load_template(
                        "status_row_transaction.json",
                        date=str(tx.get("timestamp"))[5:-3],  # MM-DD HH:MM
                        user=user_name,
                        amount=amount_str,
                        color=color,
                    )
                    list_container.append(row)

            # Web Dashboard / Looker Studio へのリンクボタンを追加
            if "footer" not in bubble:
                bubble["footer"] = {"type": "box", "layout": "vertical", "contents": []}

            import os

            # Looker StudioのURLが設定されていればそちらを優先
            # デフォルト値をコードに埋め込んでおくことで、環境変数がなくても動作するようにする
            looker_url = os.environ.get(
                "LOOKER_STUDIO_URL", "https://lookerstudio.google.com/s/uS2xDhhDtAw"
            )
            base_url = os.environ.get("APP_URL", "https://your-app.herokuapp.com")

            if looker_url:
                uri = looker_url
                label = "Looker Studioで分析"
            else:
                uri = f"{base_url}/admin/dashboard"
                label = "詳細な履歴をWebで見る"

            bubble["footer"]["contents"].append(
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {"type": "uri", "label": label, "uri": uri},
                }
            )

            line_bot_api.reply_message(
                event.reply_token,
                FlexSendMessage(alt_text="管理者ダッシュボード", contents=bubble),
            )
            return True

        else:
            # --- User View (Personal + Ranking) ---

            # A. Personal Stats
            user_info = EconomyService.get_user_info(user_id)
            if not user_info:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="ユーザー登録されていません。何か発言して登録してください。"
                    ),
                )
                return True

            study_stats = HistoryService.get_user_study_stats(user_id)
            job_history = HistoryService.get_user_job_history(user_id, limit=3)

            carousel = load_template(
                "status_user_view.json",
                user_name=user_info["display_name"],
                current_exp=user_info["current_exp"],
                weekly_study=study_stats["weekly"],
                monthly_study=study_stats["monthly"],
            )

            # Looker Studioボタンをユーザー画面にも追加
            import os

            looker_url = os.environ.get(
                "LOOKER_STUDIO_URL", "https://lookerstudio.google.com/s/uS2xDhhDtAw"
            )
            personal_bubble = carousel["contents"][0]
            if "footer" not in personal_bubble:
                personal_bubble["footer"] = {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [],
                }

            personal_bubble["footer"]["contents"].append(
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "uri",
                        "label": "Looker Studioで分析",
                        "uri": looker_url,
                    },
                }
            )

            # Job List Injection
            # carousel["contents"][0] is Personal Bubble
            # body -> contents[6] is Job List Container (index based on template structure)
            # Let's verify index:
            # 0:Name, 1:Exp, 2:Sep, 3:StudyTitle, 4:StudyBox, 5:Sep, 6:JobTitle, 7:JobBox
            job_container = carousel["contents"][0]["body"]["contents"][7]["contents"]

            if not job_history:
                job_container.append(
                    {
                        "type": "text",
                        "text": "履歴なし",
                        "size": "xs",
                        "color": "#aaaaaa",
                    }
                )
            else:
                for job in job_history:
                    row = load_template(
                        "status_row_job.json", title=job["title"], reward=job["reward"]
                    )
                    job_container.append(row)

            # B. Ranking
            ranking = HistoryService.get_leaderboard()
            # carousel["contents"][1] is Ranking Bubble
            # body -> contents[2] is Ranking List Container
            rank_container = carousel["contents"][1]["body"]["contents"][2]["contents"]

            for i, user in enumerate(ranking[:5]):  # Top 5
                rank = i + 1
                rank_color = (
                    "#FFD700"
                    if rank == 1
                    else "#C0C0C0"
                    if rank == 2
                    else "#CD7F32"
                    if rank == 3
                    else "#333333"
                )

                row = load_template(
                    "status_row_ranking.json",
                    rank=str(rank),
                    rank_color=rank_color,
                    name=user["display_name"],
                    exp=user["current_exp"],
                )
                rank_container.append(row)

            line_bot_api.reply_message(
                event.reply_token,
                FlexSendMessage(alt_text="ステータス", contents=carousel),
            )
            return True

    return False
