from services.gsheet import GSheetService
from services.job import JobService
from services.shop import ShopService


class ApprovalService:
    @staticmethod
    def get_all_pending():
        """全ての承認待ち項目をフラットなリストで取得"""
        results = []

        # 1. 勉強記録
        studies = GSheetService.get_pending_studies()
        for s in studies:
            # s keys: row_index, user_id, user_name, date, start_time, end_time
            results.append({"type": "study", "data": s})

        # 2. ジョブ完了報告
        jobs = JobService.get_pending_reviews()
        for j in jobs:
            # j keys: job_id, title, reward, status, client_id, worker_id, deadline
            data = {
                "job_id": j.get("job_id"),
                "user_id": j.get("worker_id"),
                "user_name": j.get("worker_id"),  # 名前解決できないのでID
                "job_title": j.get("title"),
                "reward": j.get("reward"),
            }
            results.append({"type": "job", "data": data})

        # 3. ショップ購入リクエスト
        shops = ShopService.get_pending_requests()
        for s in shops:
            # s keys: request_id, user_id, item_key, cost, status, time
            data = {
                "request_id": s.get("request_id") or s.get("id") or s.get("req_id"),
                "user_id": s.get("user_id"),
                "user_name": s.get("user_id"),  # 名前解決できないのでID
                "item_key": s.get("item_key"),
                "cost": s.get("cost"),
                "time": s.get("time"),
            }
            results.append({"type": "shop", "data": data})

        return results
