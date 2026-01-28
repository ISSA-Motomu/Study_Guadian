from flask import Blueprint, jsonify, request, send_from_directory, current_app
import os
import datetime
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

        total_hours = study_stats.get("total", 0)
        total_minutes_val = total_hours * 60
        rank_info = StatusService.get_rank_info(total_minutes_val)

        response_data = {
            "name": user_info.get("display_name", "Unknown"),
            "level": int(user_info.get("level", 1)),
            "exp": int(user_info.get("exp", 0)),
            "next_exp": int(user_info.get("level", 1)) * 100 + 500,
            "coins": int(user_info.get("coins", 0)),
            "total_hours": round(total_hours, 1),
            "rank_name": rank_info.get("name", "Rank E"),
            "avatar_url": user_info.get("avatar_url", ""),
        }

        return jsonify({"status": "ok", "data": response_data})

    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@web_bp.route("/api/study/subjects")
def api_study_subjects():
    """学習可能な科目リストと色定義を返す"""
    return jsonify({"status": "ok", "data": study.SUBJECT_COLORS})


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


@web_bp.route("/api/study/active_session")
def api_active_session():
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
