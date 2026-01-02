import datetime
from services.gsheet import GSheetService


class ShopService:
    @staticmethod
    def create_request(user_id, item_key, cost):
        """購入リクエストを作成"""
        sheet = GSheetService.get_worksheet("shop_requests")
        if not sheet:
            return False

        try:
            req_id = f"req_{int(datetime.datetime.now().timestamp())}"
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # ID, User, Item, Cost, Status, Time
            sheet.append_row([req_id, user_id, item_key, cost, "PENDING", now_str])
            return req_id
        except Exception as e:
            print(f"Shop Request Error: {e}")
            return False

    @staticmethod
    def get_pending_requests():
        """承認待ちの購入リクエストを取得"""
        sheet = GSheetService.get_worksheet("shop_requests")
        if not sheet:
            return []

        pending = []
        try:
            records = sheet.get_all_records()
            for row in records:
                if row.get("status") == "PENDING":
                    pending.append(row)
        except Exception as e:
            print(f"Shop Pending Error: {e}")
        return pending

    @staticmethod
    def approve_request(request_id):
        """購入リクエストを承認"""
        sheet = GSheetService.get_worksheet("shop_requests")
        if not sheet:
            return False

        try:
            # request_id は文字列であることを保証する
            cell = sheet.find(str(request_id))
            if not cell:
                return False
            sheet.update_cell(cell.row, 5, "APPROVED")

            # 商品キーを返す（アイテム名取得用）
            item_key = sheet.cell(cell.row, 3).value
            return item_key
        except Exception as e:
            print(f"Shop Approve Error: {e}")
            return False

    @staticmethod
    def deny_request(request_id):
        """購入リクエストを却下"""
        sheet = GSheetService.get_worksheet("shop_requests")
        if not sheet:
            return False

        try:
            # request_id は文字列であることを保証する
            cell = sheet.find(str(request_id))
            if not cell:
                return False
            sheet.update_cell(cell.row, 5, "DENIED")
            return True
        except Exception as e:
            print(f"Shop Deny Error: {e}")
            return False

    @staticmethod
    def get_items():
        """スプレッドシートから商品リストを取得"""
        sheet = GSheetService.get_worksheet("shop_items")
        if not sheet:
            return {}

        try:
            records = sheet.get_all_records()
            items = {}
            for row in records:
                # is_activeがTRUEのものだけ抽出
                if str(row.get("is_active")).upper() == "TRUE":
                    key = row.get("item_key")
                    items[key] = {
                        "name": row.get("name"),
                        "cost": int(row.get("cost")),
                        "description": row.get("description", ""),
                    }
            return items
        except Exception as e:
            print(f"【Error】商品リスト取得エラー: {e}")
            return {}
