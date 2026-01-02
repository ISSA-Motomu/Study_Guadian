import os
import datetime
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    FlexSendMessage,
    PostbackEvent,  # ← PostbackEventを追加
)
from dotenv import load_dotenv

from services.gsheet import GSheetService
from services.economy import EconomyService
from services.stats import SagaStats
from services.shop import ShopService
from services.job import JobService
from utils.template_loader import load_template

load_dotenv()

app = Flask(__name__)

# ... (設定部分はそのまま) ...
LINE_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)


# 簡易的な状態管理（再起動で消えます）
# {user_id: {"state": "WAITING_TITLE", "data": {...}}}
# user_states = {}


@app.route("/")
def home():
    return "Saga Guardian Active"


@app.route("/callback", methods=["POST"])
def callback():
    # ... (そのまま) ...
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


# ★★★ ここから新機能：ボタン操作の処理 ★★★
@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    # data="action=buy&item=game_30" のような文字列が来るので分解
    data = dict(x.split("=") for x in event.postback.data.split("&"))

    action = data.get("action")

    # --- 0. 勉強開始・終了 (確認後) ---
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

    elif action == "study_approve":
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="権限がありません")
            )
            return

        target_id = data.get("target")
        minutes = int(data.get("minutes"))

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

    # --- 1. 商品購入処理 (確認) ---
    elif action == "buy":
        item_key = data.get("item")
        shop_items = ShopService.get_items()
        item = shop_items.get(item_key)

        if not item:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="商品が見つかりません。")
            )
            return

        confirm_flex = load_template(
            "buy_confirm.json",
            item_name=item["name"],
            item_cost=item["cost"],
            item_key=item_key,
        )
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="購入確認", contents=confirm_flex),
        )

    # --- 1.5 商品購入処理 (実行) ---
    elif action == "confirm_buy":
        item_key = data.get("item")
        shop_items = ShopService.get_items()
        item = shop_items.get(item_key)

        if not item:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="商品が見つかりません。")
            )
            return

        # 残高チェック
        if EconomyService.check_balance(user_id, item["cost"]):
            # EXP減算 (先払い)
            new_balance = EconomyService.add_exp(
                user_id, -item["cost"], f"BUY_{item_key}"
            )

            # 親への承認リクエストカードを作成
            profile = line_bot_api.get_profile(user_id)

            approval_flex = load_template(
                "approval_request.json",
                user_name=profile.display_name,
                item_name=item["name"],
                item_cost=item["cost"],
                new_balance=new_balance,
                user_id=user_id,
                item_key=item_key,
            )

            # 購入者へのメッセージ
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(
                        text=f"✅ {item['name']} を申請しました。\n(残高: {new_balance} EXP)\n親の承認をお待ちください..."
                    ),
                    FlexSendMessage(alt_text="承認リクエスト", contents=approval_flex),
                ],
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="🚫 EXPが足りません！もっと勉強しよう。"),
            )

    # --- 2. 承認処理 (親が押す) ---
    elif action == "approve":
        # ★ここを追加：セキュリティチェック
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="🚫 あなたには承認権限がありません。\nお母さんに頼んでね！"
                ),
            )
            return

        # 権限があれば実行
        target_id = data.get("target")
        item_key = data.get("item")
        shop_items = ShopService.get_items()
        item = shop_items.get(item_key)

        item_name = item["name"] if item else "商品"

        # 弟への通知（本来は push_message ですが、無料版LINE Botの制限があるため reply で返すか、
        # あるいはグループLINE内でのやり取りなら reply で全員に見えます）
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"🙆‍♀️ 承認されました！\n\n🎟 【利用許可証】\n{item_name}\n\nこの画面を親に見せて使いましょう！"
            ),
        )

    # --- 3. 却下処理 (親が押す -> 返金) ---
    elif action == "deny":
        # 却下も管理者のみ可能にする
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="🚫 権限がありません。")
            )
            return

        target_id = data.get("target")
        cost = int(data.get("cost"))

        # 返金処理
        EconomyService.add_exp(target_id, cost, "REFUND")

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"🙅‍♀️ 却下されました。\n{cost} EXP を返金しました。ドンマイ！"
            ),
        )

    # --- 4. ジョブ関連 ---
    elif action == "job_accept":
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

    elif action == "job_approve":
        if not EconomyService.is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="権限がありません")
            )
            return

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

    # --- 5. ジョブ追加 (Admin) ---
    # elif action == "job_create_start":
    #     if not EconomyService.is_admin(user_id):
    #         return
    #
    #     # 状態を保存して会話モードへ
    #     user_states[user_id] = {"state": "WAITING_JOB_TITLE", "data": {}}
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         TextSendMessage(
    #             text="新しいお手伝いを追加します。\nまずは「タスク名」を入力してください。\n(例: お風呂掃除)"
    #         ),
    #     )


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    user_id = event.source.user_id

    # --- 0. 会話モード (状態がある場合) ---
    # if user_id in user_states:
    #     state_info = user_states[user_id]
    #     current_state = state_info["state"]
    #
    #     if msg == "キャンセル":
    #         del user_states[user_id]
    #         line_bot_api.reply_message(
    #             event.reply_token, TextSendMessage(text="キャンセルしました。")
    #         )
    #         return
    #
    #     if current_state == "WAITING_JOB_TITLE":
    #         state_info["data"]["title"] = msg
    #         state_info["state"] = "WAITING_JOB_REWARD"
    #         line_bot_api.reply_message(
    #             event.reply_token,
    #             TextSendMessage(
    #                 text=f"タスク名: {msg}\n次は「報酬(EXP)」を数字で入力してください。\n(例: 300)"
    #             ),
    #         )
    #         return

    #     elif current_state == "WAITING_JOB_REWARD":
    #         if not msg.isdigit():
    #             line_bot_api.reply_message(
    #                 event.reply_token, TextSendMessage(text="数字で入力してください。")
    #             )
    #             return
    #
    #         state_info["data"]["reward"] = int(msg)
    #         state_info["state"] = "WAITING_JOB_DEADLINE"
    #         line_bot_api.reply_message(
    #             event.reply_token,
    #             TextSendMessage(
    #                 text=f"報酬: {msg} EXP\n最後に「期限」を入力してください。\n(例: 今日中, 2026-01-05, なし)"
    #             ),
    #         )
    #         return
    #
    #     elif current_state == "WAITING_JOB_DEADLINE":
    #         title = state_info["data"]["title"]
    #         reward = state_info["data"]["reward"]
    #         deadline = msg
    #
    #         # ジョブ作成実行
    #         success, result = JobService.create_job(title, reward, deadline, user_id)
    #
    #         del user_states[user_id]  # 状態クリア
    #
    #         if success:
    #             line_bot_api.reply_message(
    #                 event.reply_token,
    #                 TextSendMessage(
    #                     text=f"✅ お手伝いを追加しました！\n\n{title}\n報酬: {reward} EXP\n期限: {deadline}"
    #                 ),
    #             )
    #
    #             # 全ユーザーへの通知
    #             try:
    #                 all_users = EconomyService.get_all_users()
    #                 recipient_ids = [
    #                     u["user_id"]
    #                     for u in all_users
    #                     if u.get("user_id") and u.get("user_id") != user_id
    #                 ]
    #
    #                 if recipient_ids:
    #                     line_bot_api.multicast(
    #                         recipient_ids,
    #                         TextSendMessage(
    #                             text=f"🆕 新しいお手伝いが追加されました！\n\n「{title}」\n報酬: {reward} EXP\n期限: {deadline}\n\nメニューの「お手伝い一覧」から確認してね！"
    #                         ),
    #                     )
    #             except Exception as e:
    #                 print(f"Job通知エラー: {e}")
    #         else:
    #             line_bot_api.reply_message(
    #                 event.reply_token,
    #                 TextSendMessage(text=f"エラーが発生しました: {result}"),
    #             )
    #         return

    # ユーザー情報を取得して登録（なければ作成）
    try:
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name
    except:
        user_name = "User"

    EconomyService.register_user(user_id, user_name)

    # 現在時刻
    now = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=9))
    )  # 日本時間
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    reply_text = ""

    # --- 1. 勉強開始 (確認) ---
    if msg == "勉強開始":
        confirm_flex = load_template(
            "confirm_dialog.json",
            text="勉強を始めますか？",
            action_data="action=start_study",
        )
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="勉強開始確認", contents=confirm_flex),
        )

    # --- 2. 勉強終了 (確認) ---
    elif msg == "勉強終了":
        confirm_flex = load_template(
            "confirm_dialog.json",
            text="勉強を終わりますか？",
            action_data="action=end_study",
        )
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="勉強終了確認", contents=confirm_flex),
        )

    # --- 4. お手伝い（ジョブ） ---
    elif msg == "ジョブ" or msg == "お手伝い":
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

    # --- 3. ショップメニュー表示 ---
    elif msg == "ショップ" or msg == "使う":
        shop_items = ShopService.get_items()
        if not shop_items:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="現在販売中の商品はありません。"),
            )
            return

        # 商品カタログFlex Messageを作成
        shop_flex = load_template("shop_list.json")
        items_contents = shop_flex["body"]["contents"]

        for key, item in shop_items.items():
            row = load_template(
                "shop_row.json", name=item["name"], cost=item["cost"], key=key
            )
            items_contents.append(row)

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="ショップメニュー", contents=shop_flex),
        )

    # ... (ランキングなどの他のコマンド) ...
