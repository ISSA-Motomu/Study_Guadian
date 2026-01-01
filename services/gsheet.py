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
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            cls._client = gspread.authorize(creds)
            cls._doc = cls._client.open_by_key(sheet_id)
        except Exception as e:
            print(f"【Error】GSheet接続失敗: {e}")

    @classmethod
    def get_worksheet(cls, sheet_name):
        """シート名を指定してワークシートを取得"""
        cls._connect()
        if not cls._doc: return None
        try:
            return cls._doc.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            print(f"【Error】シート '{sheet_name}' が見つかりません")
            return None

    @staticmethod
    def log_activity(user_id, user_name, today, time):
        """(旧互換) 学習記録用"""
        # study_log というシート名に変更してもOKですが、一旦 sheet1 (index 0) または名前指定で
        # ここでは 'study_log' というシートがあると仮定、なければ1枚目を使うロジック
        try:
            sheet = GSheetService.get_worksheet("study_log")
            if not sheet: 
                # study_logがない場合は作成するか、デフォルト1枚目を使う（運用に合わせて調整）
                # 今回は簡略化のためログは今まで通り1枚目と仮定する場合は以下
                GSheetService._connect()
                sheet = GSheetService._doc.get_worksheet(0)
            
            sheet.append_row([user_id, user_name, today, time, ""])
            return True
        except Exception as e:
            print(f"ログ記録エラー: {e}")
            return False

    @staticmethod
    def update_end_time(user_id, end_time):
        """(旧互換) 終了時刻更新"""
        # 簡易実装：1枚目のシートを見る
        GSheetService._connect()
        if not GSheetService._doc: return None
        sheet = GSheetService._doc.get_worksheet(0)
        
        all_records = sheet.get_all_values()
        target_row = None
        for i in range(len(all_records), 0, -1):
            row = all_records[i-1]
            if len(row) >= 5 and row[0] == user_id and row[4] == "":
                target_row = i
                break
        
        if target_row:
            sheet.update_cell(target_row, 5, end_time)
            return {
                "start_time": all_records[target_row-1][3],
                "row_index": target_row
            }
        return None