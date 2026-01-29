from services.gsheet import GSheetService
from services.economy import EconomyService
from utils.cache import job_list_cache, cached
import datetime


class JobService:
    @staticmethod
    def get_all_jobs_map():
        """全ジョブをID:Titleの辞書で取得（管理画面用・動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return {}

        try:
            rows = sheet.get_all_values()
            job_map = {}
            if len(rows) > 1:
                headers = rows[0]
                col_map = {str(h).strip(): i for i, h in enumerate(headers)}
                idx_jid = col_map.get("job_id")
                idx_title = col_map.get("title")

                if idx_jid is None or idx_title is None:
                    return {}

                for r in rows[1:]:
                    if len(r) > max(idx_jid, idx_title):
                        job_map[str(r[idx_jid])] = r[idx_title]
            return job_map
        except:
            return {}

    @staticmethod
    @cached(job_list_cache)
    def get_open_jobs():
        """募集中(OPEN)のジョブを取得（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return []

        jobs = []
        try:
            rows = sheet.get_all_values()
            if len(rows) > 1:
                headers = rows[0]
                col_map = {str(h).strip(): i for i, h in enumerate(headers)}

                # 必須カラム
                idx_status = col_map.get("status")
                if idx_status is None:
                    return []

                idx_jid = col_map.get("job_id")
                idx_title = col_map.get("title")
                idx_reward = col_map.get("reward")
                idx_client = col_map.get("client_id")
                idx_worker = col_map.get("worker_id")
                idx_deadline = col_map.get("deadline")

                def get_val(r, idx):
                    return r[idx] if idx is not None and idx < len(r) else ""

                for r in rows[1:]:
                    status = str(get_val(r, idx_status)).strip().upper()

                    if status == "OPEN":
                        job_data = {
                            "job_id": get_val(r, idx_jid),
                            "title": get_val(r, idx_title),
                            "reward": get_val(r, idx_reward),
                            "status": status,
                            "client_id": get_val(r, idx_client),
                            "worker_id": get_val(r, idx_worker),
                            "deadline": get_val(r, idx_deadline),
                        }
                        jobs.append(job_data)
        except Exception as e:
            print(f"Job List Error: {e}")
        return jobs

    @staticmethod
    def get_user_active_jobs(user_id):
        """ユーザーが現在担当中(ASSIGNED)のジョブを取得（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return []

        jobs = []
        try:
            rows = sheet.get_all_values()
            if len(rows) > 1:
                headers = rows[0]
                col_map = {str(h).strip(): i for i, h in enumerate(headers)}

                idx_status = col_map.get("status")
                idx_worker = col_map.get("worker_id")

                if idx_status is None or idx_worker is None:
                    return []

                idx_jid = col_map.get("job_id")
                idx_title = col_map.get("title")
                idx_reward = col_map.get("reward")
                idx_client = col_map.get("client_id")
                idx_deadline = col_map.get("deadline")

                def get_val(r, idx):
                    return r[idx] if idx is not None and idx < len(r) else ""

                for r in rows[1:]:
                    status = str(get_val(r, idx_status)).strip().upper()
                    worker = str(get_val(r, idx_worker)).strip()

                    if status == "ASSIGNED" and worker == str(user_id):
                        job_data = {
                            "job_id": get_val(r, idx_jid),
                            "title": get_val(r, idx_title),
                            "reward": get_val(r, idx_reward),
                            "status": status,
                            "client_id": get_val(r, idx_client),
                            "worker_id": worker,
                            "deadline": get_val(r, idx_deadline),
                        }
                        jobs.append(job_data)
        except Exception as e:
            print(f"My Job Error: {e}")
        return jobs

    @staticmethod
    def get_pending_reviews():
        """承認待ち(REVIEW)のジョブを取得（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return []

        reviews = []
        try:
            rows = sheet.get_all_values()
            if len(rows) > 1:
                headers = rows[0]
                col_map = {str(h).strip(): i for i, h in enumerate(headers)}

                idx_status = col_map.get("status")
                if idx_status is None:
                    return []

                idx_jid = col_map.get("job_id")
                idx_title = col_map.get("title")
                idx_reward = col_map.get("reward")
                idx_client = col_map.get("client_id")
                idx_worker = col_map.get("worker_id")
                idx_finished = col_map.get("finished_at")

                def get_val(r, idx):
                    return r[idx] if idx is not None and idx < len(r) else ""

                for r in rows[1:]:
                    status = str(get_val(r, idx_status)).strip().upper()

                    if status == "REVIEW":
                        job_data = {
                            "job_id": get_val(r, idx_jid),
                            "title": get_val(r, idx_title),
                            "reward": get_val(r, idx_reward),
                            "status": status,
                            "client_id": get_val(r, idx_client),
                            "worker_id": get_val(r, idx_worker),
                            "finished_at": get_val(r, idx_finished),
                        }
                        reviews.append(job_data)
        except Exception as e:
            print(f"Review List Error: {e}")
        return reviews

    @staticmethod
    def create_job(title, reward, deadline, client_id):
        """新しいジョブを作成（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return False, "シートエラー"

        try:
            headers = sheet.row_values(1)
            col_map = {str(h).strip(): i for i, h in enumerate(headers)}

            # Construct row based on headers
            row_data = [""] * len(headers)

            job_id = f"job_{int(datetime.datetime.now().timestamp())}"

            # Helper to set value safely
            def set_val(key, val):
                idx = col_map.get(key)
                if idx is not None:
                    row_data[idx] = val

            set_val("job_id", job_id)
            set_val("title", title)
            set_val("reward", reward)
            set_val("status", "OPEN")
            set_val("client_id", client_id)
            set_val("deadline", deadline)
            set_val("worker_id", "")  # Explicitly empty

            sheet.append_row(row_data)
            return True, job_id
        except Exception as e:
            print(f"Create Job Error: {e}")
            return False, str(e)

    @staticmethod
    def accept_job(job_id, user_id):
        """ジョブを受注する（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return False, "シートエラー"

        try:
            cell = sheet.find(str(job_id))
            if not cell:
                return False, "ジョブが見つかりません"

            headers = sheet.row_values(1)
            col_map = {str(h).strip(): i for i, h in enumerate(headers)}

            idx_status = col_map.get("status")
            idx_worker = col_map.get("worker_id")
            idx_title = col_map.get("title")

            if idx_status is None or idx_worker is None:
                return False, "シート形式エラー"

            row = cell.row
            # ステータス確認
            status = sheet.cell(row, idx_status + 1).value
            if status != "OPEN":
                return False, "この仕事はもう空いていません"

            # 更新: Status=ASSIGNED, Worker=user_id
            sheet.update_cell(row, idx_status + 1, "ASSIGNED")
            sheet.update_cell(row, idx_worker + 1, user_id)

            # ジョブ情報を返す
            title = ""
            if idx_title is not None:
                title = sheet.cell(row, idx_title + 1).value
            return True, title
        except Exception as e:
            print(f"Accept Error: {e}")
            return False, "エラーが発生しました"

    @staticmethod
    def finish_job(job_id, user_id, comment=""):
        """ジョブ完了報告（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return False, "シートエラー"

        try:
            cell = sheet.find(str(job_id))
            if not cell:
                return False, "ジョブが見つかりません"

            headers = sheet.row_values(1)
            col_map = {str(h).strip(): i for i, h in enumerate(headers)}

            idx_status = col_map.get("status")
            idx_worker = col_map.get("worker_id")
            idx_title = col_map.get("title")
            idx_reward = col_map.get("reward")
            idx_comment = col_map.get("comment")
            idx_finished = col_map.get("finished_at")

            if idx_worker is None or idx_status is None:
                return False, "シート形式エラー"

            row = cell.row
            # 本人確認
            worker = sheet.cell(row, idx_worker + 1).value
            if worker != user_id:
                return False, "担当者ではありません"

            sheet.update_cell(row, idx_status + 1, "REVIEW")

            # コメントと完了時刻を記録
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if idx_comment is not None:
                sheet.update_cell(row, idx_comment + 1, comment)
            if idx_finished is not None:
                sheet.update_cell(row, idx_finished + 1, now_str)

            title = (
                sheet.cell(row, idx_title + 1).value if idx_title is not None else ""
            )
            reward = (
                sheet.cell(row, idx_reward + 1).value if idx_reward is not None else ""
            )
            return True, {"title": title, "reward": reward}
        except Exception as e:
            return False, str(e)

    @staticmethod
    def approve_job(job_id):
        """ジョブ承認（報酬支払い）（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return False, "シートエラー"

        try:
            cell = sheet.find(str(job_id))
            if not cell:
                return False, "ジョブが見つかりません"

            headers = sheet.row_values(1)
            col_map = {str(h).strip(): i for i, h in enumerate(headers)}

            idx_status = col_map.get("status")
            idx_worker = col_map.get("worker_id")
            idx_title = col_map.get("title")
            idx_reward = col_map.get("reward")

            if idx_status is None:
                return False, "シート形式エラー"

            row = cell.row
            status = sheet.cell(row, idx_status + 1).value
            if status != "REVIEW":
                return False, "承認待ちではありません"

            # 情報取得
            title = (
                sheet.cell(row, idx_title + 1).value if idx_title is not None else ""
            )
            reward_val = (
                sheet.cell(row, idx_reward + 1).value if idx_reward is not None else "0"
            )
            if not str(reward_val).isdigit():
                reward_val = 0
            reward = int(reward_val)

            worker_id = (
                sheet.cell(row, idx_worker + 1).value if idx_worker is not None else ""
            )

            # 更新
            sheet.update_cell(row, idx_status + 1, "CLOSED")

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
        """ジョブ却下（ステータスをASSIGNEDに戻す・動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return False, "シートエラー"

        try:
            cell = sheet.find(str(job_id))
            if not cell:
                return False, "ジョブが見つかりません"

            headers = sheet.row_values(1)
            col_map = {str(h).strip(): i for i, h in enumerate(headers)}

            idx_status = col_map.get("status")
            idx_title = col_map.get("title")

            if idx_status is None:
                return False, "シート形式エラー"

            row = cell.row
            status = sheet.cell(row, idx_status + 1).value
            if status != "REVIEW":
                return False, "承認待ちではありません"

            # 更新: Status=ASSIGNED
            sheet.update_cell(row, idx_status + 1, "ASSIGNED")

            title = (
                sheet.cell(row, idx_title + 1).value if idx_title is not None else ""
            )
            return True, title
        except Exception as e:
            return False, str(e)

    @staticmethod
    def add_job(title, reward, client_id="ADMIN"):
        """新規ジョブ作成"""
        sheet = GSheetService.get_worksheet("jobs")
        if not sheet:
            return False, "Sheet not found"

        try:
            headers = sheet.row_values(1)
            col_map = {str(h).strip(): i for i, h in enumerate(headers)}

            row_data = [""] * len(headers)

            job_id = f"job_{int(datetime.datetime.now().timestamp())}"

            def set_val(key, val):
                idx = col_map.get(key)
                if idx is not None:
                    row_data[idx] = val

            set_val("job_id", job_id)
            set_val("title", title)
            set_val("reward", reward)
            set_val("status", "OPEN")
            set_val("client_id", client_id)
            set_val("worker_id", "")
            set_val("created_at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            sheet.append_row(row_data)
            # キャッシュクリア
            job_list_cache.clear()
            return True, job_id
        except Exception as e:
            return False, str(e)
