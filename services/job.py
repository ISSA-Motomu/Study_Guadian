from services.gsheet import GSheetService
from services.economy import EconomyService
from utils.cache import job_list_cache, cached
import datetime


class JobService:
    @staticmethod
    def get_all_jobs_map():
        """全ジョブをID:Titleの辞書で取得（管理画面用）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return {}

        try:
            rows = sheet.get_all_values()
            job_map = {}
            if len(rows) > 1:
                for r in rows[1:]:
                    if len(r) > 1:
                        job_map[str(r[0])] = r[1]
            return job_map
        except:
            return {}

    @staticmethod
    @cached(job_list_cache)
    def get_open_jobs():
        """募集中(OPEN)のジョブを取得"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return []

        jobs = []
        try:
            # ヘッダー依存を避けるため、全値を取得してインデックスでアクセス
            # 列: A:job_id, B:title, C:reward, D:status, E:client_id, F:worker_id, G:deadline
            rows = sheet.get_all_values()

            # ヘッダー行(1行目)をスキップ
            if len(rows) > 1:
                for r in rows[1:]:
                    # 列数が足りない場合はスキップ
                    if len(r) < 4:
                        continue

                    # D列 (Index 3) が Status
                    status = str(r[3]).strip().upper()

                    if status == "OPEN":
                        # 辞書形式に変換してリストに追加
                        job_data = {
                            "job_id": r[0],
                            "title": r[1],
                            "reward": r[2],
                            "status": status,
                            "client_id": r[4] if len(r) > 4 else "",
                            "worker_id": r[5] if len(r) > 5 else "",
                            "deadline": r[6] if len(r) > 6 else "",
                        }
                        jobs.append(job_data)
        except Exception as e:
            print(f"Job List Error: {e}")
        return jobs

    @staticmethod
    def get_user_active_jobs(user_id):
        """ユーザーが現在担当中(ASSIGNED)のジョブを取得"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return []

        jobs = []
        try:
            rows = sheet.get_all_values()
            if len(rows) > 1:
                for r in rows[1:]:
                    if len(r) < 6:
                        continue

                    status = str(r[3]).strip().upper()
                    worker = str(r[5]).strip()

                    if status == "ASSIGNED" and worker == str(user_id):
                        job_data = {
                            "job_id": r[0],
                            "title": r[1],
                            "reward": r[2],
                            "status": status,
                            "client_id": r[4],
                            "worker_id": worker,
                            "deadline": r[6] if len(r) > 6 else "",
                        }
                        jobs.append(job_data)
        except Exception as e:
            print(f"My Job Error: {e}")
        return jobs

    @staticmethod
    def get_pending_reviews():
        """承認待ち(REVIEW)のジョブを取得"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return []

        reviews = []
        try:
            rows = sheet.get_all_values()
            if len(rows) > 1:
                for r in rows[1:]:
                    if len(r) < 4:
                        continue

                    status = str(r[3]).strip().upper()
                    if status == "REVIEW":
                        job_data = {
                            "job_id": r[0],
                            "title": r[1],
                            "reward": r[2],
                            "status": status,
                            "client_id": r[4] if len(r) > 4 else "",
                            "worker_id": r[5] if len(r) > 5 else "",
                        }
                        reviews.append(job_data)
        except Exception as e:
            print(f"Review List Error: {e}")
        return reviews

    @staticmethod
    def create_job(title, reward, deadline, client_id):
        """新しいジョブを作成"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return False, "シートエラー"

        try:
            # ID生成 (job_timestamp)
            job_id = f"job_{int(datetime.datetime.now().timestamp())}"

            # 列: job_id, title, reward, status, client_id, worker_id, deadline
            # ※ deadlineはG列(7列目)に追加と仮定
            sheet.append_row([job_id, title, reward, "OPEN", client_id, "", deadline])
            return True, job_id
        except Exception as e:
            print(f"Create Job Error: {e}")
            return False, str(e)

    @staticmethod
    def accept_job(job_id, user_id):
        """ジョブを受注する"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return False, "シートエラー"

        try:
            cell = sheet.find(str(job_id))
            if not cell:
                return False, "ジョブが見つかりません"

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
        if not sheet:
            return False, "シートエラー"

        try:
            cell = sheet.find(str(job_id))
            if not cell:
                return False, "ジョブが見つかりません"

            row = cell.row
            # 本人確認 (F列=6)
            worker = sheet.cell(row, 6).value
            if worker != user_id:
                return False, "担当者ではありません"

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
        if not sheet:
            return False, "シートエラー"

        try:
            cell = sheet.find(str(job_id))
            if not cell:
                return False, "ジョブが見つかりません"

            row = cell.row
            status = sheet.cell(row, 4).value
            if status != "REVIEW":
                return False, "承認待ちではありません"

            # 情報取得
            title = sheet.cell(row, 2).value
            reward = int(sheet.cell(row, 3).value)
            worker_id = sheet.cell(row, 6).value

            # 更新
            sheet.update_cell(row, 4, "CLOSED")

            # 支払い
            new_balance = EconomyService.add_exp(worker_id, reward, f"JOB_{job_id}")

            return True, {
                "worker_id": worker_id,
                "title": title,
                "reward": reward,
                "balance": new_balance,
            }
        except Exception as e:
            return False, str(e)

    @staticmethod
    def reject_job(job_id):
        """ジョブ却下（ステータスをASSIGNEDに戻す）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return False, "シートエラー"

        try:
            cell = sheet.find(str(job_id))
            if not cell:
                return False, "ジョブが見つかりません"

            row = cell.row
            status = sheet.cell(row, 4).value
            if status != "REVIEW":
                return False, "承認待ちではありません"

            # 更新: Status=ASSIGNED
            sheet.update_cell(row, 4, "ASSIGNED")

            title = sheet.cell(row, 2).value
            return True, title
        except Exception as e:
            return False, str(e)
