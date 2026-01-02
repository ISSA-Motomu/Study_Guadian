import os
import json
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
            # A:ID, B:名前, C:日付, D:開始, E:終了, F:ステータス, G:Duration, H:Rank, I:Subject
            sheet.append_row(
                [user_id, user_name, today, time, "", "STARTED", "", "", subject]
            )
            return True
        except Exception as e:
            print(f"ログ記録エラー: {e}")
            return False

    @staticmethod
    def update_end_time(user_id, end_time):
        """終了時刻を study_log シートに更新"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return None

        all_records = sheet.get_all_values()
        target_row = None

        # 後ろから検索
        for i in range(len(all_records), 0, -1):
            row = all_records[i - 1]
            # ID一致 かつ 終了時刻(E列=index4)が空
            if len(row) >= 5 and row[0] == user_id and row[4] == "":
                target_row = i
                break

        if target_row:
            # E列(5):終了時刻, F列(6):ステータス
            sheet.update_cell(target_row, 5, end_time)
            sheet.update_cell(target_row, 6, "PENDING")
            return {
                "start_time": all_records[target_row - 1][3],
                "row_index": target_row,
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
                # F列(index 5)が "PENDING"
                if len(row) >= 6 and row[5] == "PENDING":
                    pending.append(
                        {
                            "row_index": i,
                            "user_id": row[0],
                            "user_name": row[1],
                            "date": row[2],
                            "start_time": row[3],
                            "end_time": row[4],
                        }
                    )
        except Exception as e:
            print(f"Pending Study Error: {e}")
        return pending

    @staticmethod
    def approve_study(row_index):
        """学習記録を承認済みに更新"""
        sheet = GSheetService.get_worksheet("study_log")
        if not sheet:
            return False
        try:
            # 既に承認済みかチェック (F列=6)
            current_status = sheet.cell(row_index, 6).value
            if current_status == "APPROVED":
                return False

            sheet.update_cell(row_index, 6, "APPROVED")
            return True
        except:
            return False
