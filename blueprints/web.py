from flask import Blueprint, jsonify, request, send_from_directory, current_app
import os
import datetime
from services.job import JobService
from services.shop import ShopService
from services.gsheet import GSheetService
from services.economy import EconomyService
from services.history import HistoryService
from services.status_service import StatusService
from services.stats import SagaStats
from bot_instance import line_bot_api
from utils.template_loader import load_template
from linebot.models import FlexSendMessage
from handlers import study

web_bp = Blueprint("web", __name__)


@web_bp.route("/api/admin/users")
def api_admin_users():
    """全ユーザーリストを返す"""
    users = EconomyService.get_all_users()
    # フロントエンドで使いやすい形式に整形
    user_list = []
    for u in users:
        user_list.append(
            {"user_id": u.get("user_id"), "user_name": u.get("display_name", "Unknown")}
        )
    return jsonify({"status": "success", "users": user_list})


@web_bp.route("/api/admin/add_task", methods=["POST"])
def api_admin_add_task():
    """タスク追加"""
    data = request.json
    title = data.get("title")
    reward = data.get("reward")
    # client_id = data.get("user_id") # 未使用のためコメントアウト

    if not title:
        return jsonify({"status": "error", "message": "Title required"}), 400

    # JobService.add_jobを使用するように修正（create_jobは前回までの実装か誤記）
    success, msg = JobService.add_job(title, reward)
    if success:
        return jsonify({"status": "success", "job_id": msg})
    else:
        return jsonify({"status": "error", "message": msg}), 500


@web_bp.route("/api/admin/add_item", methods=["POST"])
def api_admin_add_item():
    """アイテム追加"""
    data = request.json
    name = data.get("name")
    cost = data.get("cost")
    description = data.get("description", "")

    if not name:
        return jsonify({"status": "error", "message": "Name required"}), 400

    if ShopService.add_item(name, cost, description):
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Failed to add item"}), 500


@web_bp.route("/api/admin/grant_points", methods=["POST"])
def api_admin_grant_points():
    """ポイント付与"""
    data = request.json
    user_id = data.get("user_id")
    amount = data.get("amount")

    if not user_id or amount is None:
        return jsonify({"status": "error", "message": "Missing params"}), 400

    if EconomyService.add_exp(user_id, int(amount), "ADMIN_GRANT"):
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Failed to grant"}), 500


@web_bp.route("/app/dashboard")
def liff_dashboard():
    """LIFFのトップページ (ダッシュボード) を返す"""
    directory = os.path.join(current_app.root_path, "templates", "liff")
    return send_from_directory(directory, "index.html")


@web_bp.route("/api/user/update_profile", methods=["POST"])
def api_update_profile():
    """LIFFから取得した最新のプロフィール情報でDBを更新する"""
    data = request.json
    user_id = data.get("user_id")
    display_name = data.get("display_name")
    avatar_url = data.get("avatar_url")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing user_id"}), 400

    # ユーザーが存在するか確認、いなければ登録フローが必要だが
    # LIFFが開けている時点で登録済みか、もしくはここで登録してもよいが
    # 基本は登録済みのはず。

    if EconomyService.update_user_profile(user_id, display_name, avatar_url):
        return jsonify({"status": "ok"})
    else:
        # 更新失敗（ユーザーがいない場合など）
        # 新規登録を試みる？ 今回はシンプルにエラーもしくは無視
        return jsonify({"status": "error", "message": "Update failed"}), 500


@web_bp.route("/api/user/<user_id>/status")
def api_user_status(user_id):
    """ユーザーのステータス情報をJSONで返すAPI"""
    try:
        user_info = EconomyService.get_user_info(user_id)
        if not user_info:
            return jsonify({"status": "error", "message": "User not found"}), 404

        study_stats = HistoryService.get_user_study_stats(user_id)

        total_minutes = study_stats.get("total", 0)
        total_hours = total_minutes / 60

        # ランク判定には分を使用
        rank_info = StatusService.get_rank_info(total_minutes)

        # レベル計算 (例: 1時間でレベルアップ)
        level = int(total_hours) + 1

        # 次のレベルまでの経験値 (次の時間までの残り分数など)
        # ここでは簡易的に 1時間 = 100 EXP として表現
        exp = int((total_minutes % 60) / 60 * 100)
        next_exp = 100

        response_data = {
            "name": user_info.get("display_name", "Unknown"),
            "level": level,
            "exp": exp,
            "next_exp": next_exp,
            "gold": int(
                user_info.get("current_exp", 0)
            ),  # シートのcurrent_expをGoldとして扱う
            "gems": 0,  # ジェムは一先ず0固定
            "total_hours": round(total_hours, 1),
            "rank_name": rank_info.get("name", "Rank E"),
            "avatar_url": user_info.get("avatar_url", ""),
            "role": user_info.get("role", "USER"),
        }

        return jsonify({"status": "ok", "data": response_data})

    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@web_bp.route("/api/study/subjects")
def api_study_subjects():
    """学習可能な科目リストと色定義を返す"""
    return jsonify({"status": "ok", "data": study.SUBJECT_COLORS})


@web_bp.route("/api/shop/items")
def api_shop_items():
    """ショップの商品リストを返す"""
    items = ShopService.get_items()
    # OrderedDict to list
    items_list = []
    for key, val in items.items():
        val["key"] = key
        items_list.append(val)
    return jsonify({"status": "ok", "data": items_list})


@web_bp.route("/api/shop/buy", methods=["POST"])
def api_shop_buy():
    """商品購入リクエスト"""
    data = request.json
    user_id = data.get("user_id")
    item_key = data.get("item_key")
    comment = data.get("comment", "")

    if not user_id or not item_key:
        return jsonify({"status": "error", "message": "Missing parameters"}), 400

    items = ShopService.get_items()
    item = items.get(item_key)
    if not item:
        return jsonify({"status": "error", "message": "Item not found"}), 404

    cost = item["cost"]

    # 残高チェック
    if not EconomyService.check_balance(user_id, cost):
        return jsonify({"status": "error", "message": "Not enough coins"}), 400

    # ポイント減算
    EconomyService.add_exp(user_id, -cost, f"BUY_{item_key}")

    # リクエスト作成
    user_info = EconomyService.get_user_info(user_id)
    user_name = user_info.get("display_name", "Unknown") if user_info else "Unknown"

    ShopService.create_request(user_id, item_key, cost, comment, user_name)

    # TODO: AdminへのLINE通知などもここで行うと親切

    return jsonify({"status": "ok", "message": "Requested"})


@web_bp.route("/api/study/start", methods=["POST"])
def api_start_study():
    """学習セッションを開始する"""
    data = request.json
    user_id = data.get("user_id")
    subject = data.get("subject")

    if not user_id or not subject:
        return jsonify({"status": "error", "message": "Missing parameters"}), 400

    try:
        user_info = EconomyService.get_user_info(user_id)
        user_name = user_info["display_name"] if user_info else "User"

        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        if GSheetService.log_activity(user_id, user_name, today, current_time, subject):
            color = study.SUBJECT_COLORS.get(subject, "#27ACB2")
            try:
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
            except Exception as push_error:
                print(f"Push Message Error: {push_error}")
                # LINE通知失敗でも処理は継続する

            return jsonify({"status": "ok", "start_time": current_time})
        else:
            return jsonify(
                {"status": "error", "message": "Failed to log activity"}
            ), 500

    except Exception as e:
        print(f"Study Start Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@web_bp.route("/api/user/<user_id>/active_session")
def api_active_session(user_id):
    # 簡易実装: リクエストがあればアクティブとみなすか、本来はDB問い合わせが必要
    # ユーザーが「勉強中」かどうかを判定するロジック
    return jsonify({"status": "ok", "active": False})


@web_bp.route("/api/study/finish", methods=["POST"])
def api_finish_study():
    data = request.json
    user_id = data.get("user_id")
    memo = data.get("memo", "")

    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    current_time = now.strftime("%H:%M:%S")

    user_info = EconomyService.get_user_info(user_id)
    user_name = user_info["display_name"] if user_info else "User"

    result = GSheetService.update_end_time(user_id, current_time, user_name)
    if result:
        # メモを保存
        try:
            # study_logの該当行にmemoカラムがあれば書き込む
            sheet = GSheetService.get_worksheet("study_log")
            if sheet:
                headers = sheet.row_values(1)
                col_map = {str(h).strip(): i for i, h in enumerate(headers)}
                idx_memo = col_map.get("memo")
                if idx_memo is not None:
                    sheet.update_cell(result["row_index"], idx_memo + 1, memo)
        except Exception as e:
            print(f"Memo保存エラー: {e}")

        start_time_str = result["start_time"]
        try:
            start_dt = datetime.datetime.strptime(start_time_str, "%H:%M:%S")
            end_dt = datetime.datetime.strptime(current_time, "%H:%M:%S")
            if end_dt < start_dt:
                end_dt += datetime.timedelta(days=1)
            duration = end_dt - start_dt
            minutes = int(duration.total_seconds() / 60)
            if minutes > 90:
                minutes = 90

            stats = SagaStats.calculate(minutes)
            if stats:
                GSheetService.update_study_stats(
                    result["row_index"], minutes, stats["rank"]
                )

            return jsonify({"status": "ok", "minutes": minutes})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "error", "message": "No active session"}), 404


@web_bp.route("/api/study/cancel", methods=["POST"])
def api_cancel_study():
    data = request.json
    user_id = data.get("user_id")

    if GSheetService.cancel_study(user_id):
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "Failed to cancel"}), 400


@web_bp.route("/api/study/pause", methods=["POST"])
def api_pause_study():
    data = request.json
    user_id = data.get("user_id")
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    current_time = now.strftime("%H:%M:%S")

    result = GSheetService.update_end_time(user_id, current_time)
    if result:
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400


# --- ADMIN API ---
