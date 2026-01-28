from services.gsheet import GSheetService
import datetime
import json


class EconomyService:
    @staticmethod
    def check_balance(user_id, cost):
        """残高が足りているか確認（足りていればTrue）"""
        user = EconomyService.get_user_info(user_id)
        if not user:
            return False

        # current_expが数値であることを確認しつつ比較
        try:
            current = int(user.get("current_exp", 0))
            return current >= cost
        except:
            return False

    @staticmethod
    def is_admin(user_id):
        """管理権限を持っているか確認"""
        user = EconomyService.get_user_info(user_id)
        if not user:
            return False
        return user.get("role") == "ADMIN"

    @staticmethod
    def get_user_info(user_id):
        """ユーザー情報を取得（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("users")
        if not sheet:
            return None

        # get_all_records is safe enough for reading dicts, but to be consistent with "check headers":
        try:
            rows = sheet.get_all_values()
            if len(rows) > 1:
                headers = rows[0]
                col_map = {str(h).strip(): i for i, h in enumerate(headers)}
                idx_uid = col_map.get("user_id")

                if idx_uid is None:
                    return None

                for r in rows[1:]:
                    if len(r) > idx_uid and str(r[idx_uid]) == str(user_id):
                        # Construct dict
                        return {
                            k: (r[v] if v < len(r) else "") for k, v in col_map.items()
                        }
        except:
            pass
        return None

    @staticmethod
    def get_all_users():
        """全ユーザー情報を取得（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("users")
        if not sheet:
            return []

        try:
            rows = sheet.get_all_values()
            users = []
            if len(rows) > 1:
                headers = rows[0]
                col_map = {str(h).strip(): i for i, h in enumerate(headers)}

                for r in rows[1:]:
                    u = {k: (r[v] if v < len(r) else "") for k, v in col_map.items()}
                    users.append(u)
            return users
        except:
            return []

    @staticmethod
    def get_admin_users():
        """Admin権限を持つユーザーのリストを取得"""
        users = EconomyService.get_all_users()
        admins = [u for u in users if u.get("role") == "ADMIN"]
        return admins

    @staticmethod
    def register_user(user_id, display_name):
        """新規ユーザー登録（口座開設・動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("users")
        if not sheet:
            return False

        # すでにいるか確認
        if EconomyService.get_user_info(user_id):
            return True  # 登録済み

        try:
            headers = sheet.row_values(1)
            col_map = {str(h).strip(): i for i, h in enumerate(headers)}

            row_data = [""] * len(headers)

            def set_val(key, val):
                idx = col_map.get(key)
                if idx is not None:
                    row_data[idx] = val

            set_val("user_id", user_id)
            set_val("display_name", display_name)
            set_val("current_exp", 0)
            set_val("total_study_time", 0)
            set_val("role", "USER")
            set_val("inventory_json", "{}")
            set_val("rank", "E")

            sheet.append_row(row_data)
            return True
        except:
            return False

    @staticmethod
    def update_user_profile(user_id, display_name, avatar_url):
        """ユーザーの表示名とアイコンURLを更新（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("users")
        if not sheet:
            return False

        try:
            cell = sheet.find(user_id)
            if cell:
                headers = sheet.row_values(1)
                col_map = {str(h).strip(): i for i, h in enumerate(headers)}

                idx_name = col_map.get("display_name")
                # スプレッドシート側で avatar_url カラムがなくても name が変われば更新したい
                if idx_name is not None:
                    sheet.update_cell(cell.row, idx_name + 1, display_name)

                idx_avatar = col_map.get("avatar_url")
                if idx_avatar is not None and avatar_url:
                    sheet.update_cell(cell.row, idx_avatar + 1, avatar_url)

                return True
            return False
        except Exception as e:
            print(f"Update Profile Error: {e}")
            return False

    @staticmethod
    def update_user_rank(user_id, rank):
        """ユーザーのランクを更新（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("users")
        if not sheet:
            return False

        try:
            cell = sheet.find(user_id)
            if cell:
                headers = sheet.row_values(1)
                col_map = {str(h).strip(): i for i, h in enumerate(headers)}
                idx_rank = col_map.get("rank")
                if idx_rank is not None:
                    sheet.update_cell(cell.row, idx_rank + 1, rank)
                    return True
            return False
        except Exception as e:
            print(f"Update Rank Error: {e}")
            return False

    @staticmethod
    def update_user_achievements(user_id, achievements_str):
        """ユーザーの実績リストを更新（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("users")
        if not sheet:
            return False

        try:
            cell = sheet.find(user_id)
            if cell:
                headers = sheet.row_values(1)
                col_map = {str(h).strip(): i for i, h in enumerate(headers)}
                # Looking for 'achievements', usually not present in initial schema but added here
                idx_ach = col_map.get("achievements")
                if idx_ach is None:
                    # Fallback check for column 8 (H) or just print error?
                    # Ideally we should not fallback to hardcoded if we want to be strict.
                    # But if the column doesn't exist, we can't update it unless we find empty col?
                    # Assuming 'achievements' header must exist.
                    return False

                sheet.update_cell(cell.row, idx_ach + 1, achievements_str)
                return True
            return False
        except Exception as e:
            print(f"Update Achievements Error: {e}")
            return False

    @staticmethod
    def update_user_role(user_id, role):
        """ユーザーの権限(Role)を更新（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("users")
        if not sheet:
            return False

        try:
            cell = sheet.find(user_id)
            if cell:
                headers = sheet.row_values(1)
                col_map = {str(h).strip(): i for i, h in enumerate(headers)}
                idx_role = col_map.get("role")
                if idx_role is not None:
                    sheet.update_cell(cell.row, idx_role + 1, role)
                    return True
            return False
        except Exception as e:
            print(f"Update Role Error: {e}")
            return False

    @staticmethod
    def reset_user(user_id):
        """ユーザー情報をリセット（削除）"""
        sheet = GSheetService.get_worksheet("users")
        if not sheet:
            return False

        try:
            cell = sheet.find(user_id)
            if cell:
                sheet.delete_rows(cell.row)
                return True
            return False
        except Exception as e:
            print(f"Reset User Error: {e}")
            return False

    @staticmethod
    def get_user_inventory(user_id):
        """ユーザーの所持品リストを取得"""
        # Uses get_user_info which is already refactored
        user = EconomyService.get_user_info(user_id)
        if not user:
            return []

        inventory_json = user.get("inventory_json", "{}")
        if not inventory_json:
            inventory_json = "{}"

        try:
            inventory_dict = json.loads(inventory_json)
        except:
            inventory_dict = {}

        # 辞書からリスト形式に変換 (表示用)
        item_master = {
            "ticket_1.5x": {"name": "ポイント 1.5倍", "icon": "🎟", "type": "item"},
            "shield_chores": {"name": "絶対防御", "icon": "🛡", "type": "item"},
            "supple_focus": {"name": "集中サプリ", "icon": "💊", "type": "item"},
            "bonus_100": {"name": "臨時ボーナス", "icon": "💸", "type": "item"},
            # Badges
            "badge_bath": {"name": "お風呂博士", "icon": "🛁", "type": "badge"},
            "badge_print": {"name": "暗記王", "icon": "🧠", "type": "badge"},
            "badge_early": {"name": "早起き名人", "icon": "☀️", "type": "badge"},
            "badge_clean": {"name": "お掃除隊長", "icon": "🧹", "type": "badge"},
            "badge_cook": {"name": "料理の鉄人", "icon": "🍳", "type": "badge"},
        }

        items = []
        for item_key, count in inventory_dict.items():
            if count > 0:
                master = item_master.get(
                    item_key, {"name": item_key, "icon": "📦", "type": "item"}
                )
                items.append(
                    {
                        "key": item_key,
                        "name": master["name"],
                        "icon": master["icon"],
                        "type": master.get("type", "item"),
                        "count": count,
                    }
                )
        return items

    @staticmethod
    def get_user_badges(user_id):
        """ユーザーの所持バッジのみを取得"""
        inventory = EconomyService.get_user_inventory(user_id)
        return [item for item in inventory if item.get("type") == "badge"]

    @staticmethod
    def add_inventory_item(user_id, item_key, count=1):
        """インベントリにアイテムを追加（動的カラムマッピング）"""
        sheet = GSheetService.get_worksheet("users")
        if not sheet:
            return False

        try:
            cell = sheet.find(user_id)
            if not cell:
                return False

            row_num = cell.row

            headers = sheet.row_values(1)
            col_map = {str(h).strip(): i for i, h in enumerate(headers)}
            idx_inv = col_map.get("inventory_json")
            if idx_inv is None:
                return False

            inv_cell = sheet.cell(row_num, idx_inv + 1)
            inv_json = inv_cell.value

            try:
                inv_dict = json.loads(inv_json) if inv_json else {}
            except:
                inv_dict = {}

            current_count = inv_dict.get(item_key, 0)
            inv_dict[item_key] = current_count + count

            sheet.update_cell(row_num, idx_inv + 1, json.dumps(inv_dict))
            return True
        except:
            return False

    @staticmethod
    def add_exp(user_id, amount, related_id="STUDY"):
        """EXPを加算（減算ならマイナス）し、履歴に残す（動的カラムマッピング）"""
        users_sheet = GSheetService.get_worksheet("users")
        tx_sheet = GSheetService.get_worksheet("transactions")

        if not users_sheet or not tx_sheet:
            return False

        try:
            # 1. ユーザーを探して残高更新
            cell = users_sheet.find(user_id)
            if not cell:
                return False

            headers_u = users_sheet.row_values(1)
            col_map_u = {str(h).strip(): i for i, h in enumerate(headers_u)}
            idx_name = col_map_u.get("display_name")
            idx_exp = col_map_u.get("current_exp")

            if idx_name is None or idx_exp is None:
                return False

            row_num = cell.row
            user_name = users_sheet.cell(row_num, idx_name + 1).value
            current_exp_cell = users_sheet.cell(row_num, idx_exp + 1)

            try:
                current_val = int(current_exp_cell.value)
            except:
                current_val = 0
            new_exp = current_val + amount

            # 2. 取引履歴(Transaction)を記録
            tx_id = f"tx_{int(datetime.datetime.now().timestamp())}"
            tx_type = "REWARD" if amount > 0 else "SPEND"
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            headers_tx = tx_sheet.row_values(1)
            col_map_tx = {str(h).strip(): i for i, h in enumerate(headers_tx)}

            row_data_tx = [""] * len(headers_tx)

            def set_val_tx(key, val, alt_keys=None):
                idx = col_map_tx.get(key)
                if idx is None and alt_keys:
                    for ak in alt_keys:
                        idx = col_map_tx.get(ak)
                        if idx is not None:
                            break
                if idx is not None:
                    row_data_tx[idx] = val

            set_val_tx("tx_id", tx_id)
            set_val_tx("user_id", user_id)
            set_val_tx("amount", amount)
            set_val_tx("tx_type", tx_type)
            set_val_tx("related_id", related_id)
            set_val_tx("timestamp", now_str, ["time"])
            set_val_tx("user_name", user_name)

            try:
                tx_sheet.append_row(row_data_tx)
            except Exception as e:
                print(f"Transaction Log Error: {e}")
                return False

            # 3. 残高更新
            try:
                users_sheet.update_cell(row_num, idx_exp + 1, new_exp)
            except Exception as e:
                print(f"Balance Update Error: {e}")
                return False

            return new_exp
        except Exception as e:
            print(f"Add Exp Error: {e}")
            return False
