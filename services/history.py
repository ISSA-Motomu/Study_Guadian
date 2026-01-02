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
            records = sheet.get_all_records()
            # 新しい順にソート
            sorted_records = sorted(
                records, key=lambda x: x.get("timestamp", ""), reverse=True
            )
            return sorted_records
        except Exception as e:
            print(f"All History Error: {e}")
            return []

    @staticmethod
    def get_admin_history(limit=10):
        """管理用：最近の取引履歴を取得"""
        sheet = GSheetService.get_worksheet("transactions")
        if not sheet:
            return []

        try:
            records = sheet.get_all_records()
            # 新しい順にソート
            sorted_records = sorted(
                records, key=lambda x: x.get("timestamp", ""), reverse=True
            )
            return sorted_records[:limit]
        except Exception as e:
            print(f"Admin History Error: {e}")
            return []

    @staticmethod
    def get_user_study_stats(user_id):
        """ユーザーの学習履歴統計（週間・月間）"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return {"weekly": 0, "monthly": 0, "total": 0}

        now = datetime.datetime.now()
        week_start = now - datetime.timedelta(days=7)
        month_start = now - datetime.timedelta(days=30)

        stats = {"weekly": 0, "monthly": 0, "total": 0}

        try:
            records = sheet.get_all_values()
            # Header skip
            for row in records[1:]:
                # row: [id, name, date, start, end, status]
                if len(row) < 6:
                    continue
                if row[0] != user_id:
                    continue
                if row[5] != "APPROVED":
                    continue  # 承認済みのみ

                date_str = row[2]
                start_str = row[3]
                end_str = row[4]

                try:
                    log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")

                    # 時間計算
                    s = datetime.datetime.strptime(start_str, "%H:%M:%S")
                    e = datetime.datetime.strptime(end_str, "%H:%M:%S")
                    if e < s:
                        e += datetime.timedelta(days=1)
                    minutes = int((e - s).total_seconds() / 60)

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
        """ユーザーの直近7日間の日別学習時間"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return []

        now = datetime.datetime.now()
        # 今日を含む過去7日間
        dates = [(now - datetime.timedelta(days=i)) for i in range(6, -1, -1)]
        # date_str keys: "YYYY-MM-DD"
        daily_map = {d.strftime("%Y-%m-%d"): 0 for d in dates}

        # 曜日ラベル用
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]

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
                if date_str in daily_map:
                    start_str = row[3]
                    end_str = row[4]
                    try:
                        s = datetime.datetime.strptime(start_str, "%H:%M:%S")
                        e = datetime.datetime.strptime(end_str, "%H:%M:%S")
                        if e < s:
                            e += datetime.timedelta(days=1)
                        minutes = int((e - s).total_seconds() / 60)
                        daily_map[date_str] += minutes
                    except:
                        pass
        except Exception as e:
            print(f"Daily Stats Error: {e}")

        # リスト形式に変換
        result = []
        for d in dates:
            d_str = d.strftime("%Y-%m-%d")
            mins = daily_map[d_str]
            label = f"{d.month}/{d.day}({weekdays[d.weekday()]})"
            result.append({"date": d_str, "label": label, "minutes": mins})

        return result

    @staticmethod
    def get_user_job_history(user_id, limit=5):
        """ユーザーの完了したジョブ履歴"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return []

        jobs = []
        try:
            records = sheet.get_all_records()
            user_jobs = [
                r
                for r in records
                if str(r.get("worker_id")) == user_id and r.get("status") == "CLOSED"
            ]
            # ID(timestamp)で降順ソートと仮定
            # job_id = job_1234567890
            sorted_jobs = sorted(
                user_jobs, key=lambda x: x.get("job_id", ""), reverse=True
            )
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
            records = sheet.get_all_records()
            user_jobs = [
                r
                for r in records
                if str(r.get("worker_id")) == user_id and r.get("status") == "CLOSED"
            ]
            return len(user_jobs)
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
            ranking = []

            for u in all_users:
                uid = str(u.get("user_id"))
                role = u.get("role")
                if role != "USER":
                    continue

                earned = user_exp.get(uid, 0)
                ranking.append(
                    {
                        "user_id": uid,
                        "display_name": u.get("display_name"),
                        "weekly_exp": earned,
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
