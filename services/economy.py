from services.gsheet import GSheetService
import datetime

class EconomyService:
    
    @staticmethod
    def get_user_info(user_id):
        """ユーザー情報を取得（なければNone）"""
        sheet = GSheetService.get_worksheet("users")
        if not sheet: return None
        
        # 全データを取得して検索（人数が増えたらfindメソッドなどへ最適化推奨）
        records = sheet.get_all_records() # ヘッダーがある前提
        for user in records:
            if str(user.get("user_id")) == user_id:
                return user
        return None

    @staticmethod
    def register_user(user_id, display_name):
        """新規ユーザー登録（口座開設）"""
        sheet = GSheetService.get_worksheet("users")
        if not sheet: return False
        
        # すでにいるか確認
        if EconomyService.get_user_info(user_id):
            return True # 登録済み
            
        # 新規登録 (初期EXP: 0, Role: USER)
        # 列順: user_id, display_name, current_exp, total_study_time, role
        sheet.append_row([user_id, display_name, 0, 0, "USER"])
        return True

    @staticmethod
    def add_exp(user_id, amount, related_id="STUDY"):
        """EXPを加算（減算ならマイナス）し、履歴に残す"""
        users_sheet = GSheetService.get_worksheet("users")
        tx_sheet = GSheetService.get_worksheet("transactions")
        
        if not users_sheet or not tx_sheet: return False
        
        # 1. ユーザーを探して残高更新
        cell = users_sheet.find(user_id)
        if not cell: return False
        
        row_num = cell.row
        # current_exp は C列(3列目)と仮定
        current_exp_cell = users_sheet.cell(row_num, 3) 
        new_exp = int(current_exp_cell.value) + amount
        users_sheet.update_cell(row_num, 3, new_exp)
        
        # 2. 取引履歴(Transaction)を記録
        # 列: tx_id, user_id, amount, tx_type, related_id, timestamp
        tx_id = f"tx_{int(datetime.datetime.now().timestamp())}"
        tx_type = "REWARD" if amount > 0 else "SPEND"
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        tx_sheet.append_row([tx_id, user_id, amount, tx_type, related_id, now_str])
        
        return new_exp