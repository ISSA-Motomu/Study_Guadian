import os
from flask import Flask, render_template
from dotenv import load_dotenv

from services.history import HistoryService
from services.economy import EconomyService
from services.gsheet import GSheetService
from services.shop import ShopService
from services.job import JobService
from handlers import study

# Import Blueprints
from blueprints.bot import bot_bp
from blueprints.web import web_bp

load_dotenv()

app = Flask(__name__, template_folder="templates/html")

# Register Blueprints
app.register_blueprint(bot_bp)
app.register_blueprint(web_bp)


@app.route("/")
def wake_up():
    return "I am awake! Saga Guardian Active", 200


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

    return render_template("admin_dashboard.html", transactions=transactions)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
