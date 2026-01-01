from services.gsheet import GSheetService
from services.economy import EconomyService

class JobService:
    @staticmethod
    def get_open_jobs():
        """募集中(OPEN)のジョブを取得"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet: return []
        
        jobs = []
        try:
            records = sheet.get_all_records()
            for row in records:
                if row.get("status") == "OPEN":
                    jobs.append(row)
        except Exception as e:
            print(f"Job List Error: {e}")
        return jobs

    @staticmethod
    def get_user_active_jobs(user_id):
        """ユーザーが現在担当中(ASSIGNED)のジョブを取得"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet: return []
        
        jobs = []
        try:
            records = sheet.get_all_records()
            for row in records:
                if row.get("status") == "ASSIGNED" and str(row.get("worker_id")) == user_id:
                    jobs.append(row)
        except Exception as e:
            print(f"My Job Error: {e}")
        return jobs

    @staticmethod
    def accept_job(job_id, user_id):
        """ジョブを受注する"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet: return False, "シートエラー"
        
        try:
            cell = sheet.find(job_id)
            if not cell: return False, "ジョブが見つかりません"
            
            row = cell.row
            # ステータス確認 (D列=4)
            status = sheet.cell(row, 4).value
            if status != "OPEN":
                return False, "この仕事はもう空いていません"
            
            # 更新: Status=ASSIGNED, Worker=user_id
            sheet.update_cell(row, 4, "ASSIGNED")
            sheet.update_cell(row, 6, user_id)
            
            # ジョブ情報を返す
            title = sheet.cell(row, 2).value
            return True, title
        except Exception as e:
            print(f"Accept Error: {e}")
            return False, "エラーが発生しました"

    @staticmethod
    def finish_job(job_id, user_id):
        """ジョブ完了報告"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet: return False, "シートエラー"
        
        try:
            cell = sheet.find(job_id)
            if not cell: return False, "ジョブが見つかりません"
            
            row = cell.row
            # 本人確認 (F列=6)
            worker = sheet.cell(row, 6).value
            if worker != user_id: return False, "担当者ではありません"
            
            sheet.update_cell(row, 4, "REVIEW")
            
            title = sheet.cell(row, 2).value
            reward = sheet.cell(row, 3).value
            return True, {"title": title, "reward": reward}
        except Exception as e:
            return False, str(e)

    @staticmethod
    def approve_job(job_id):
        """ジョブ承認（報酬支払い）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet: return False, "シートエラー"
        
        try:
            cell = sheet.find(job_id)
            if not cell: return False, "ジョブが見つかりません"
            
            row = cell.row
            status = sheet.cell(row, 4).value
            if status != "REVIEW": return False, "承認待ちではありません"
            
            # 情報取得
            title = sheet.cell(row, 2).value
            reward = int(sheet.cell(row, 3).value)
            worker_id = sheet.cell(row, 6).value
            
            # 更新
            sheet.update_cell(row, 4, "CLOSED")
            
            # 支払い
            new_balance = EconomyService.add_exp(worker_id, reward, f"JOB_{job_id}")
            
            return True, {"worker_id": worker_id, "title": title, "reward": reward, "balance": new_balance}
        except Exception as e:
            return False, str(e)
