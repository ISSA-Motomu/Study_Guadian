import os
from flask import (
    Flask,
    request,
    abort,
    render_template,
    jsonify,
    session,
    send_from_directory,
)
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    PostbackEvent,
    FlexSendMessage,
)
from dotenv import load_dotenv
import datetime
from utils.template_loader import load_template
from services.gsheet import GSheetService
from bot_instance import line_bot_api, handler
from handlers import study, shop, job, admin, status, common, help, gacha, mission
from services.history import HistoryService
from services.economy import EconomyService
from utils.debouncer import Debouncer

load_dotenv()

from services.status_service import StatusService
from services.stats import SagaStats  # 追加
from utils.achievements import AchievementManager  # 追加

app = Flask(__name__, template_folder="templates/html")


# --- LIFF / Web App Routes ---


@app.route("/app/dashboard")
def liff_dashboard():
    """LIFFのトップページ (ダッシュボード) を返す"""
    # テンプレートフォルダ外のファイルを返すため、send_from_directoryを使用
    # app.root_path を使って絶対パスを構築
    directory = os.path.join(app.root_path, "templates", "liff")
    return send_from_directory(directory, "index.html")


@app.route("/api/user/<user_id>/status")
def api_user_status(user_id):
    """ユーザーのステータス情報をJSONで返すAPI"""
    try:
        # A. 基本情報取得
        user_info = EconomyService.get_user_info(user_id)
        if not user_info:
            # ユーザーが存在しない場合
            return jsonify({"status": "error", "message": "User not found"}), 404

        # B. 各種統計取得
        study_stats = HistoryService.get_user_study_stats(user_id)
        # job_count = HistoryService.get_user_job_count(user_id)

        # C. ランク計算等
        total_minutes = (
            study_stats.get("total", 0) * 60
        )  # totalは時間単位？ HistoryServiceの実装によるが、一旦分換算の想定

        # HistoryService.get_user_study_stats は float(hours) を返していると仮定するか実装確認が必要
        # handlers/status.py ではこうなっている: user_data["total_study_time"] = study_stats["total"]
        # StatusService.get_rank_info(total_minutes)

        # ここでは簡易的に実装。本来はService層に移譲すべき。
        total_hours = study_stats.get("total", 0)
        total_minutes_val = total_hours * 60
        rank_info = StatusService.get_rank_info(total_minutes_val)

        # レベル計算ロジック (commonあたりにあるはずだが、簡易計算)
        # 一旦 user_info の情報を信じる

        # レスポンスデータの構築
        response_data = {
            "name": user_info.get("name", "Unknown"),
            "level": int(user_info.get("level", 1)),
            "exp": int(user_info.get("exp", 0)),
            "next_exp": int(user_info.get("level", 1)) * 100 + 500,  # 仮のNextEXP計算式
            "coins": int(user_info.get("coins", 0)),
            "total_hours": round(total_hours, 1),
            "rank_name": rank_info.get("name", "Rank E"),
            "avatar_url": user_info.get("avatar_url", ""),  # DBにあれば
        }

        return jsonify({"status": "ok", "data": response_data})

    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/study/subjects")
def api_study_subjects():
    """学習可能な科目リストと色定義を返す"""
    # handlers.study.SUBJECT_COLORS を利用
    return jsonify({"status": "ok", "data": study.SUBJECT_COLORS})


@app.route("/api/study/start", methods=["POST"])
def api_start_study():
    """学習セッションを開始する"""
    data = request.json
    user_id = data.get("user_id")
    subject = data.get("subject")

    if not user_id or not subject:
        return jsonify({"status": "error", "message": "Missing parameters"}), 400

    try:
        # ユーザー情報の取得（名前解決用）
        user_info = EconomyService.get_user_info(user_id)
        user_name = user_info["display_name"] if user_info else "User"

        # 現在時刻
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        # GSheetに記録
        if GSheetService.log_activity(user_id, user_name, today, current_time, subject):
            # LINEにPush通知 (Flex Message)
            color = study.SUBJECT_COLORS.get(subject, "#27ACB2")
            bubble = load_template(
                "study_session.json",
                subject=subject,
                start_time=current_time,
                color=color,
            )
            line_bot_api.push_message(
                user_id,
                FlexSendMessage(alt_text="勉強中...", contents=bubble),
            )
            return jsonify({"status": "ok", "start_time": current_time})
        else:
            return jsonify(
                {"status": "error", "message": "Failed to log activity"}
            ), 500

    except Exception as e:
        print(f"Study Start Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/")
def home():
    return "Saga Guardian Active"


# app.py の一番上あたりに追加
@app.route("/")
def wake_up():
    return "I am awake!", 200


from services.gsheet import GSheetService


@app.route("/cron/check_timeout")
def cron_check_timeout():
    # タイムアウトしたセッションを確認
    expired_sessions = GSheetService.check_timeout_sessions(timeout_minutes=90)

    if expired_sessions:
        # 通知と状態更新
        study.process_timeout_sessions(expired_sessions)
        return f"Processed {len(expired_sessions)} sessions.", 200

    return "No expired sessions.", 200


@app.route("/admin/dashboard")
def admin_dashboard():
    # 本来は認証が必要だが、簡易的にURLを知っている人のみアクセス可能とする
    # もしくはクエリパラメータで ?key=secret_key のように簡易認証を入れても良い

    transactions = HistoryService.get_all_transactions()

    # ユーザーIDを名前に変換
    users = EconomyService.get_all_users()
    user_map = {str(u["user_id"]): u["display_name"] for u in users}

    # 詳細情報解決用のマップ
    job_map = JobService.get_all_jobs_map()
    shop_items = ShopService.get_items()

    for tx in transactions:
        uid = str(tx.get("user_id"))
        tx["user_name"] = user_map.get(uid, uid[:4])

        # 取引内容の解決
        rtype = tx.get("tx_type")
        rid = str(tx.get("related_id", ""))

        desc = rid
        if rtype == "REWARD":
            if rid == "STUDY_REWARD":
                desc = "✏️ 勉強報酬"
            elif rid.startswith("JOB_"):
                jid = rid.replace("JOB_", "")
                jtitle = job_map.get(jid, "不明なタスク")
                desc = f"🧹 {jtitle}"
        elif rtype == "SPEND":
            if rid.startswith("BUY_"):
                ikey = rid.replace("BUY_", "")
                iname = shop_items.get(ikey, {}).get("name", ikey)
                desc = f"🛒 {iname}"
        elif rtype == "REFUND":
            desc = "↩️ 返金"

        tx["description"] = desc

    return render_template("html/admin_dashboard.html", transactions=transactions)


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    data_str = event.postback.data

    # 連打防止 (5秒間)
    if Debouncer.is_locked(user_id, data_str):
        return

    # data="action=buy&item=game_30" のような文字列が来るので分解
    data = dict(x.split("=") for x in data_str.split("&"))
    action = data.get("action")

    # グループ判定
    is_group = event.source.type != "user"

    # 各ハンドラに委譲
    if common.handle_postback(event, action, data):
        return
    if study.handle_postback(event, action, data):
        return
    if shop.handle_postback(event, action, data):
        return

    # グループでは管理機能を使えないようにする
    if not is_group:
        if admin.handle_postback(event, action, data):
            return

    if job.handle_postback(event, action, data):
        return
    if mission.handle_postback(event, action, data):
        return
    if status.handle_postback(event, action, data):
        return

    # どのハンドラも処理しなかった場合
    print(f"Unhandled Postback: {action}")


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    user_id = event.source.user_id

    # 連打防止 (メッセージも3秒間ロック)
    if Debouncer.is_locked(user_id, msg):
        return

    # グループ判定
    is_group = event.source.type != "user"

    # 共通処理（ユーザー登録・オンボーディング）
    if common.handle_message(event, msg):
        return

    # 各ハンドラに委譲
    if help.handle_message(event, msg):
        return
    if study.handle_message(event, msg):
        return
    if shop.handle_message(event, msg):
        return
    if job.handle_message(event, msg):
        return
    if mission.handle_message(event, msg):
        return

    # グループでは管理機能を使えないようにする
    if not is_group:
        if admin.handle_message(event, msg):
            return

    if status.handle_message(event, msg):
        return
    if gacha.handle_message(event, msg):
        return

    # どのハンドラも処理しなかった場合
    # 必要であれば「わかりません」などを返す
    pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
