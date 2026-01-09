import os
import json
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials


class GSheetService:
    _instance = None
    _client = None
    _doc = None

    @classmethod
    def _connect(cls):
        """スプレッドシートへの接続を確立（内部利用）"""
        if cls._client and cls._doc:
            return

        try:
            creds_json = os.environ.get("GOOGLE_CREDENTIALS")
            sheet_id = os.environ.get("SPREADSHEET_ID")

            if not creds_json or not sheet_id:
                print("【Error】環境変数が不足しています")
                return

            creds_dict = json.loads(creds_json)
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            cls._client = gspread.authorize(creds)
            cls._doc = cls._client.open_by_key(sheet_id)
        except Exception as e:
            print(f"【Error】GSheet接続失敗: {e}")

    @classmethod
    def get_worksheet(cls, sheet_name):
        """シート名を指定してワークシートを取得"""
        cls._connect()
        if not cls._doc:
            return None
        try:
            return cls._doc.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            print(f"【Error】シート '{sheet_name}' が見つかりません")
            return None

    @staticmethod
    def log_activity(user_id, user_name, today, time, subject=""):
        """学習記録ログを study_log シートに保存"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            print("【Error】study_log シートが見つかりません。作成してください。")
            return False

        try:
            # ユーザー指定順序に対応:
            # A:display_name, B:date, C:start_time, D:end_time, E:status,
            # F:duration_min, G:rank_score, H:subject, I:comment, J:concentration
            # K:user_id (System ID for tracking)
            sheet.append_row(
                [
                    user_name,  # A: display_name
                    today,  # B: date
                    time,  # C: start_time
                    "",  # D: end_time
                    "STARTED",  # E: status
                    "",  # F: duration_min
                    "",  # G: rank_score
                    subject,  # H: subject
                    "",  # I: comment
                    "",  # J: concentration
                    user_id,  # K: user_id
                ]
            )
            return True
        except Exception as e:
            print(f"ログ記録エラー: {e}")
            return False

    @staticmethod
    def cancel_study(user_id, user_name=None):
        """学習記録をキャンセル（削除またはステータス変更）"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return False

        all_records = sheet.get_all_values()
        target_row = None

        # 後ろから検索
        # IDがK列(index 10)にあるか、NameがA列(index 0)にあるか確認
        for i in range(len(all_records), 0, -1):
            row = all_records[i - 1]
            if len(row) < 5:
                continue

            # 判定ロジック
            is_match = False
            # ID check (Index 10)
            if len(row) >= 11 and str(row[10]) == str(user_id):
                is_match = True
            # Fallback Name check (Index 0)
            elif user_name and str(row[0]) == str(user_name):
                is_match = True
            # Legacy check (if row has ID at 0? No, unsafe to assume)

            # End Time (Index 3) が空なら対象
            if is_match and row[3] == "":
                target_row = i
                break

        if target_row:
            try:
                # Status is Index 4 (E列)
                sheet.update_cell(target_row, 5, "CANCELLED")
                return True
            except Exception as e:
                print(f"Cancel Study Error: {e}")
                return False
        return False

    @staticmethod
    def update_end_time(user_id, end_time, user_name=None):
        """終了時刻を study_log シートに更新"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return None

        all_records = sheet.get_all_values()
        target_row = None

        # 後ろから検索
        for i in range(len(all_records), 0, -1):
            row = all_records[i - 1]
            if len(row) < 5:
                continue

            # Match Logic
            is_match = False
            if len(row) >= 11 and str(row[10]).strip() == str(user_id):
                is_match = True
            elif user_name and str(row[0]).strip() == str(user_name):
                is_match = True

            # EndTime (IDX 3), Status (IDX 4)
            if is_match:
                end_val = str(row[3]).strip()
                status_val = str(row[4]).strip()

                if end_val == "" and status_val == "STARTED":
                    target_row = i
                    break

        if target_row:
            # D列(4):終了時刻, E列(5):ステータス
            sheet.update_cell(target_row, 4, end_time)
            sheet.update_cell(target_row, 5, "PENDING")

            # Subject is Index 7 (H列)
            subject = ""
            if len(all_records[target_row - 1]) >= 8:
                subject = all_records[target_row - 1][7]

            # Start Time is Index 2 (C列)
            start_time = all_records[target_row - 1][2]

            return {
                "start_time": start_time,
                "row_index": target_row,
                "subject": subject,
            }
        return None

    @staticmethod
    def update_study_stats(row_index, duration, rank):
        """学習時間とランクを study_log シートに追記"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return False
        try:
            # G列(7): Duration, H列(8): Rank
            sheet.update_cell(row_index, 7, duration)
            sheet.update_cell(row_index, 8, rank)
            return True
        except Exception as e:
            print(f"Stats Update Error: {e}")
            return False

    @staticmethod
    def update_study_details(row_index, comment, concentration):
        """学習の成果と集中度を study_log シートに追記"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return False
        try:
            # J列(10): Comment, K列(11): Concentration
            sheet.update_cell(row_index, 10, comment)
            sheet.update_cell(row_index, 11, concentration)
            return True
        except Exception as e:
            print(f"Details Update Error: {e}")
            return False

    @staticmethod
    def get_pending_studies():
        """承認待ちの学習記録を取得"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return []

        pending = []
        try:
            records = sheet.get_all_values()
            # ヘッダー飛ばす
            for i, row in enumerate(records[1:], start=2):
                if len(row) < 5:
                    continue
                # Status (IDX 4)
                if row[4] == "PENDING":
                    # ID (IDX 10) or Name (IDX 0)
                    uid = row[10] if len(row) >= 11 else ""
                    pending.append(
                        {
                            "row_index": i,
                            "user_id": uid,
                            "user_name": row[0],  # Name
                            "date": row[1],  # Date
                            "start_time": row[2],  # Start
                            "end_time": row[3],  # End
                        }
                    )
        except Exception as e:
            print(f"Pending Study Error: {e}")
        return pending

    @staticmethod
    def get_user_latest_pending_session(user_id, user_name=None):
        """ユーザーの最新のPENDING（コメント待ち）セッションを取得"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return None

        all_records = sheet.get_all_values()

        # 後ろから検索
        for i in range(len(all_records), 0, -1):
            row = all_records[i - 1]
            if len(row) < 6:
                continue

            is_match = False
            # ID (A=0)
            if str(row[0]).strip() == str(user_id):
                is_match = True
            # Name (B=1)
            elif user_name and str(row[1]).strip() == str(user_name):
                is_match = True

            # Status (F=IDX 5) == PENDING
            if is_match and row[5] == "PENDING":
                # Comment (J=IDX 9) check
                comment = row[9] if len(row) >= 10 else ""
                if not comment:
                    # Duration (G=IDX 6), Subject (I=IDX 8)
                    dur_str = row[6] if len(row) >= 7 else "0"

                    return {
                        "row_index": i,
                        "start_time": row[3],  # Start D=3
                        "minutes": int(dur_str) if dur_str.isdigit() else 0,
                        "subject": row[8] if len(row) >= 9 else "",  # Subject I=8
                        "state": "WAITING_COMMENT",
                    }
        return None

    @staticmethod
    def approve_study(row_index):
        """学習記録を承認済みに更新"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return False
        try:
            # Status (F=IDX 5, Column 6)
            current_status = sheet.cell(row_index, 6).value
            if current_status == "APPROVED":
                return False

            sheet.update_cell(row_index, 6, "APPROVED")
            return True
        except:
            return False

    @staticmethod
    def reject_study(row_index):
        """学習記録を却下（REJECTED）に更新"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return False
        try:
            # Status (F=IDX 5, Column 6)
            current_status = sheet.cell(row_index, 6).value
            if current_status == "APPROVED":
                return False

            sheet.update_cell(row_index, 6, "REJECTED")
            return True
        except:
            return False

    @staticmethod
    def check_timeout_sessions(timeout_minutes=90):
        """制限時間を超えた学習セッションを強制終了する"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return []

        try:
            all_records = sheet.get_all_values()
            expired_sessions = []

            now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

            for i in range(1, len(all_records)):
                row = all_records[i]
                if len(row) < 6:
                    continue

                status = row[5]  # IDX 5 status
                end_time = row[4]  # IDX 4 end_time

                if status == "STARTED" and end_time == "":
                    date_str = row[2]  # IDX 2 date
                    start_time_str = row[3]  # IDX 3 start_time

                    try:
                        start_dt = datetime.datetime.strptime(
                            f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M:%S"
                        )
                        start_dt = start_dt.replace(
                            tzinfo=datetime.timezone(datetime.timedelta(hours=9))
                        )

                        duration = now - start_dt
                        duration_minutes = int(duration.total_seconds() / 60)

                        if duration_minutes >= timeout_minutes:
                            force_end_dt = start_dt + datetime.timedelta(
                                minutes=timeout_minutes
                            )
                            force_end_time_str = force_end_dt.strftime("%H:%M:%S")

                            row_index = i + 1
                            # Update End(IDX 4 -> Col 5)
                            # Update Status(IDX 5 -> Col 6)
                            sheet.update_cell(row_index, 5, force_end_time_str)
                            sheet.update_cell(row_index, 6, "PENDING")

                            # UID IDX 0 (A)
                            uid = row[0]

                            expired_sessions.append(
                                {
                                    "user_id": uid,
                                    "row_index": row_index,
                                    "minutes": timeout_minutes,
                                    "subject": row[8]
                                    if len(row) > 8
                                    else "",  # Subject I=8
                                    "start_time": start_time_str,
                                }
                            )
                    except Exception as e:
                        print(f"Date Parse Error: {e}")
                        continue

            return expired_sessions

        except Exception as e:
            print(f"Check Timeout Error: {e}")
            return []
