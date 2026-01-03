from linebot.models import TextSendMessage, FlexSendMessage
from bot_instance import line_bot_api
from services.economy import EconomyService
from services.history import HistoryService
from services.status_service import StatusService
from utils.template_loader import load_template
from handlers import common


def handle_postback(event, action, data):
    line_user_id = event.source.user_id
    user_id = common.get_current_user_id(line_user_id)

    if action == "show_history":
        # ユーザー自身の履歴を表示
        # HistoryService.get_all_transactions() は全履歴なので、ユーザーでフィルタリングが必要
        # または HistoryService に get_user_history を追加するのが良いが、
        # ここでは既存の get_all_transactions を使ってフィルタリングする

        all_tx = HistoryService.get_all_transactions()
        user_tx = [tx for tx in all_tx if str(tx.get("user_id")) == user_id]

        # 直近10件
        history = user_tx[:10]

        bubble = load_template("status_admin_view.json")
        # タイトル変更
        bubble["header"]["contents"][0]["text"] = "HISTORY"
        bubble["header"]["backgroundColor"] = "#444444"

        # body -> contents[2] is the list container
        list_container = bubble["body"]["contents"][2]["contents"]
        # Clear existing placeholder if any (though template usually has empty list or placeholder)
        # The template loader loads the JSON. Let's assume it's empty or we append.
        # Actually status_admin_view.json might have some structure.
        # Let's just clear and append.
        list_container.clear()

        if not history:
            list_container.append(
                {
                    "type": "text",
                    "text": "履歴なし",
                    "size": "sm",
                    "color": "#aaaaaa",
                    "align": "center",
                }
            )
        else:
            for tx in history:
                amount = int(tx.get("amount", 0))
                color = "#ff5555" if amount > 0 else "#5555ff"
                amount_str = f"+{amount}" if amount > 0 else str(amount)

                # Description resolution
                desc = str(tx.get("related_id", ""))
                rtype = tx.get("tx_type")

                if rtype == "REWARD":
                    if desc == "STUDY_REWARD":
                        desc = "勉強報酬"
                    elif desc.startswith("JOB_"):
                        desc = "お手伝い報酬"
                    elif desc.startswith("ADMIN_GRANT"):
                        desc = "ボーナス"
                elif rtype == "SPEND":
                    if desc.startswith("BUY_"):
                        desc = "アイテム購入"

                row = load_template(
                    "status_row_transaction.json",
                    date=str(tx.get("timestamp"))[5:-3],
                    user=desc,  # Reuse 'user' field for description
                    amount=amount_str,
                    color=color,
                )
                list_container.append(row)

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="履歴", contents=bubble),
        )
        return True

    return False


def handle_message(event, text):
    line_user_id = event.source.user_id
    user_id = common.get_current_user_id(line_user_id)

    if text in ["状況", "ステータス", "status", "詳細ステータス"]:
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
            job_count = HistoryService.get_user_job_count(user_id)
            inventory = EconomyService.get_user_inventory(user_id)
            weekly_ranking = HistoryService.get_weekly_exp_ranking()

            # Prepare data for StatusService
            user_data = user_info.copy()
            user_data["total_study_time"] = study_stats["total"]
            user_data["total_jobs"] = job_count

            if text == "詳細ステータス":
                # 週間・月間学習グラフ表示
                weekly_history = HistoryService.get_user_weekly_daily_stats(user_id)
                monthly_history = HistoryService.get_user_monthly_weekly_stats(user_id)

                carousel = StatusService.create_report_carousel(
                    user_data, weekly_history, monthly_history, inventory
                )
                alt_text = "学習レポート"

                line_bot_api.reply_message(
                    event.reply_token,
                    FlexSendMessage(alt_text=alt_text, contents=carousel),
                )
            else:
                # 勲章ホーム画面表示
                bubble = StatusService.create_medal_home_gui(user_data, weekly_ranking)
                alt_text = "ステータス"

                line_bot_api.reply_message(
                    event.reply_token,
                    FlexSendMessage(alt_text=alt_text, contents=bubble),
                )
            return True

    return False
