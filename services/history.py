import datetime
from services.gsheet import GSheetService
from services.economy import EconomyService


class HistoryService:
    @staticmethod
    def get_all_transactions():
        """全取引履歴を取得（Web表示用）"""
        sheet = GSheetService.get_worksheet("transactions")
        if not sheet:
            return []

        try:
            # get_all_records はヘッダー依存で不安定なため get_all_values を使用
            # 想定カラム: tx_id, user_id, amount, tx_type, related_id, timestamp, user_name
            rows = sheet.get_all_values()

            records = []
            # ヘッダー行判定 (1行目が "tx_id" ならヘッダーとみなす)
            start_index = 0
            if len(rows) > 0 and str(rows[0][0]) == "tx_id":
                start_index = 1

            for r in rows[start_index:]:
                if len(r) < 6:
                    continue

                records.append(
                    {
                        "tx_id": r[0],
                        "user_id": r[1],
                        "amount": int(r[2])
                        if r[2] and str(r[2]).lstrip("-").isdigit()
                        else 0,
                        "tx_type": r[3],
                        "related_id": r[4],
                        "timestamp": r[5],
                        "user_name": r[6] if len(r) > 6 else "",
                    }
                )

            # 新しい順にソート (timestamp降順)
            sorted_records = sorted(
                records, key=lambda x: str(x.get("timestamp", "")), reverse=True
            )
            return sorted_records
        except Exception as e:
            print(f"All History Error: {e}")
            return []

    @staticmethod
    def get_admin_history(limit=10):
        """管理用：最近の取引履歴を取得"""
        all_tx = HistoryService.get_all_transactions()
        return all_tx[:limit]

    @staticmethod
    def is_first_study_today(user_id):
        """その日の最初の勉強かどうか判定"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return False

        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        today_str = now.strftime("%Y-%m-%d")

        try:
            records = sheet.get_all_values()
            # Header skip
            count = 0
            for row in records[1:]:
                # row: [id, name, date, start, end, status]
                if len(row) < 6:
                    continue
                if str(row[0]) != str(user_id):
                    continue
                if row[2] == today_str:
                    status = row[5]
                    if status not in ["CANCELLED", "REJECTED"]:
                        count += 1

            # 今のセッションも含まれるため、1なら初回
            return count == 1

        except Exception as e:
            print(f"First Study Check Error: {e}")
            return False

    @staticmethod
    def get_today_study_count(user_id):
        """今日の勉強回数を取得"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return 0

        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        today_str = now.strftime("%Y-%m-%d")

        try:
            records = sheet.get_all_values()
            count = 0
            for row in records[1:]:
                if len(row) < 6:
                    continue
                if str(row[0]) != str(user_id):
                    continue
                if row[2] == today_str:
                    status = row[5]
                    if status not in ["CANCELLED", "REJECTED"]:
                        count += 1
            return count
        except Exception as e:
            print(f"Study Count Error: {e}")
            return 0

    @staticmethod
    def get_user_study_stats(user_id):
        """ユーザーの学習履歴統計（週間・月間）※カレンダー基準"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return {"weekly": 0, "monthly": 0, "total": 0}

        now = datetime.datetime.now()
        # 今週の月曜日 (0:00:00)
        week_start = (now - datetime.timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # 今月の1日 (0:00:00)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        stats = {"weekly": 0, "monthly": 0, "total": 0}

        try:
            records = sheet.get_all_values()
            # Header skip
            for row in records[1:]:
                # row header:
                # 0: id, 1: name, 2: date, 3: start, 4: end, 5: status, 6: duration(min)
                if len(row) < 7:
                    continue
                if row[0] != user_id:
                    continue
                if row[5] != "APPROVED":
                    continue  # 承認済みのみ

                date_str = row[2]

                try:
                    log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")

                    # 時間計算 (以前は start/end から計算していたが、duration_min (index 6) を使用するように変更)
                    minutes = 0
                    if row[6] and str(row[6]).isdigit():
                        minutes = int(row[6])

                    stats["total"] += minutes

                    if log_date >= week_start:
                        stats["weekly"] += minutes

                    if log_date >= month_start:
                        stats["monthly"] += minutes

                except:
                    continue

        except Exception as e:
            print(f"Study Stats Error: {e}")

        return stats

    @staticmethod
    def get_user_weekly_daily_stats(user_id):
        """ユーザーの直近7日間の日別学習時間（教科別）"""
        now = datetime.datetime.now()
        # 今日を含む過去7日間
        dates = [(now - datetime.timedelta(days=i)) for i in range(6, -1, -1)]
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]

        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            # シートがない場合でも空のデータを返す
            return [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "label": f"{d.month}/{d.day}({weekdays[d.weekday()]})",
                    "minutes": 0,
                    "subjects": {},
                }
                for d in dates
            ]

        # date_str keys: "YYYY-MM-DD"
        # Value structure: {"total": 0, "subjects": {"math": 0, "eng": 0, ...}}
        daily_map = {
            d.strftime("%Y-%m-%d"): {"total": 0, "subjects": {}} for d in dates
        }

        try:
            records = sheet.get_all_values()
            for row in records[1:]:
                if len(row) < 7:
                    continue
                if row[0] != user_id:
                    continue
                if row[5] != "APPROVED":
                    continue

                date_str = row[2]
                if date_str in daily_map:
                    subject = row[8] if len(row) >= 9 else "その他"
                    if not subject:
                        subject = "その他"

                    try:
                        # 時間計算: duration (index 6) を使用
                        minutes = 0
                        if row[6] and str(row[6]).isdigit():
                            minutes = int(row[6])

                        daily_map[date_str]["total"] += minutes
                        if subject not in daily_map[date_str]["subjects"]:
                            daily_map[date_str]["subjects"][subject] = 0
                        daily_map[date_str]["subjects"][subject] += minutes
                    except:
                        pass
        except Exception as e:
            print(f"Daily Stats Error: {e}")

        # リスト形式に変換
        result = []
        for d in dates:
            d_str = d.strftime("%Y-%m-%d")
            data = daily_map[d_str]
            label = f"{d.month}/{d.day}({weekdays[d.weekday()]})"
            result.append(
                {
                    "date": d_str,
                    "label": label,
                    "minutes": data["total"],
                    "subjects": data["subjects"],
                }
            )
        return result

    @staticmethod
    def get_user_monthly_weekly_stats(user_id):
        """ユーザーの直近4週間の週別学習時間（教科別）"""
        now = datetime.datetime.now()
        # 過去4週間 (28日間)
        # 4つの期間を作る: [3週間前, 2週間前, 1週間前, 今週]
        weeks = []
        for i in range(3, -1, -1):
            # i=3: 21-27日前, i=0: 0-6日前
            end_d = now - datetime.timedelta(days=i * 7)
            start_d = end_d - datetime.timedelta(days=6)

            # 日付比較用にdateオブジェクトにする
            weeks.append(
                {
                    "start_date": start_d.date(),
                    "end_date": end_d.date(),
                    "label": f"{start_d.month}/{start_d.day}~",
                    "total": 0,
                    "subjects": {},
                }
            )

        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            # シートがない場合でも空のデータを返す
            result = []
            for w in weeks:
                result.append({"label": w["label"], "minutes": 0, "subjects": {}})
            return result

        try:
            records = sheet.get_all_values()
            for row in records[1:]:
                if len(row) < 6:
                    continue
                if row[0] != user_id:
                    continue
                if row[5] != "APPROVED":
                    continue

                date_str = row[2]
                try:
                    log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

                    # どの週に該当するかチェック
                    target_week = None
                    for w in weeks:
                        if w["start_date"] <= log_date <= w["end_date"]:
                            target_week = w
                            break

                    if target_week:
                        subject = row[8] if len(row) >= 9 else "その他"
                        if not subject:
                            subject = "その他"

                        # 時間計算: duration (index 6) を使用
                        minutes = 0
                        if row[6] and str(row[6]).isdigit():
                            minutes = int(row[6])

                        target_week["total"] += minutes
                        if subject not in target_week["subjects"]:
                            target_week["subjects"][subject] = 0
                        target_week["subjects"][subject] += minutes

                except:
                    pass
        except Exception as e:
            print(f"Monthly Stats Error: {e}")

        # 結果整形
        result = []
        for w in weeks:
            result.append(
                {"label": w["label"], "minutes": w["total"], "subjects": w["subjects"]}
            )

        return result

    @staticmethod
    def get_user_job_history(user_id, limit=5):
        """ユーザーの完了したジョブ履歴"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return []

        jobs = []
        try:
            rows = sheet.get_all_values()
            if len(rows) > 1:
                # Header: job_id, title, reward, status, client_id, worker_id, deadline
                for r in rows[1:]:
                    if len(r) < 6:
                        continue

                    # Check worker_id (F=5) and status (D=3)
                    if str(r[5]) == user_id and str(r[3]) == "CLOSED":
                        jobs.append(
                            {
                                "job_id": r[0],
                                "title": r[1],
                                "reward": r[2],
                                "status": r[3],
                                "client_id": r[4],
                                "worker_id": r[5],
                                "deadline": r[6] if len(r) > 6 else "",
                            }
                        )

            # Sort by job_id desc
            sorted_jobs = sorted(jobs, key=lambda x: x.get("job_id", ""), reverse=True)
            return sorted_jobs[:limit]
        except Exception as e:
            print(f"Job History Error: {e}")
            return []

    @staticmethod
    def get_user_job_count(user_id):
        """ユーザーの完了したジョブ総数"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return 0

        try:
            rows = sheet.get_all_values()
            count = 0
            if len(rows) > 1:
                for r in rows[1:]:
                    if len(r) < 6:
                        continue
                    if str(r[5]) == user_id and str(r[3]) == "CLOSED":
                        count += 1
            return count
        except Exception as e:
            print(f"Job Count Error: {e}")
            return 0

    @staticmethod
    def get_leaderboard():
        """全ユーザーのランキング（EXP順）"""
        users = EconomyService.get_all_users()
        # current_expでソート
        try:
            ranked = sorted(
                users, key=lambda x: int(x.get("current_exp", 0)), reverse=True
            )
            return ranked
        except:
            return users

    @staticmethod
    def get_weekly_exp_ranking():
        """今週の獲得EXPランキング（USERのみ）"""
        sheet = GSheetService.get_worksheet("transactions")
        if not sheet:
            return []

        now = datetime.datetime.now()
        week_start = now - datetime.timedelta(days=7)

        user_exp = {}  # {user_id: total_exp}

        try:
            records = sheet.get_all_records()
            for tx in records:
                # tx: tx_id, user_id, amount, tx_type, related_id, timestamp
                if tx.get("tx_type") != "REWARD":
                    continue

                ts_str = str(tx.get("timestamp"))
                try:
                    # フォーマットは "YYYY-MM-DD HH:MM:SS"
                    tx_date = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                except:
                    continue

                if tx_date < week_start:
                    continue

                uid = str(tx.get("user_id"))
                amount = int(tx.get("amount", 0))
                user_exp[uid] = user_exp.get(uid, 0) + amount

            # ユーザー情報と結合してフィルタリング
            all_users = EconomyService.get_all_users()

            # Admin IDを特定 (重複エントリ対策: どこかにADMINがあればそのIDはAdminとみなす)
            admin_ids = set()
            for u in all_users:
                if str(u.get("role", "")).strip().upper() == "ADMIN":
                    admin_ids.add(str(u.get("user_id")))

            ranking = []

            for u in all_users:
                uid = str(u.get("user_id"))

                # Adminとして特定されたIDはスキップ
                if uid in admin_ids:
                    continue

                role = str(u.get("role", "")).strip().upper()
                if role != "USER":
                    continue

                earned = user_exp.get(uid, 0)
                ranking.append(
                    {
                        "user_id": uid,
                        "display_name": u.get("display_name"),
                        "weekly_exp": earned,
                        "total_study_time": u.get("total_study_time", 0),
                    }
                )

            # ソート
            ranking.sort(key=lambda x: x["weekly_exp"], reverse=True)

            # 順位付け
            for i, r in enumerate(ranking):
                r["rank"] = i + 1

            return ranking

        except Exception as e:
            print(f"Weekly Ranking Error: {e}")
            return []
