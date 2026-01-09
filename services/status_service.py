import urllib.parse
import json
from services.stats import SagaStats
from utils.achievements import AchievementManager


class StatusService:
    @staticmethod
    def format_duration(total_minutes):
        """分を H時間M分 表記に変換"""
        total_minutes = int(total_minutes)
        if total_minutes < 60:
            return f"{total_minutes}m"
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if minutes == 0:
            return f"{hours}h"
        return f"{hours}h{minutes}m"

    @staticmethod
    def get_rank_info(total_minutes):
        """累計勉強時間からランク情報を取得"""
        # ランク定義 (難易度調整版)
        # E: 0-300 (5h)
        # D: 300-1200 (20h)
        # C: 1200-3600 (60h)
        # B: 3600-7200 (120h)
        # A: 7200-12000 (200h)
        # S: 12000+ (200h+)
        if total_minutes >= 12000:
            return {
                "name": "Rank S: 伝説の勇者",
                "color": "#9932CC",
                "next": None,
                "base": 12000,
                "img": "rank_s.png",
            }
        elif total_minutes >= 7200:
            return {
                "name": "Rank A: 黄金の騎士",
                "color": "#FFD700",
                "next": 12000,
                "base": 7200,
                "img": "rank_a.png",
            }
        elif total_minutes >= 3600:
            return {
                "name": "Rank B: 銀の熟練者",
                "color": "#C0C0C0",
                "next": 7200,
                "base": 3600,
                "img": "rank_b.png",
            }
        elif total_minutes >= 1200:
            return {
                "name": "Rank C: 銅の戦士",
                "color": "#CD7F32",
                "next": 3600,
                "base": 1200,
                "img": "rank_c.png",
            }
        elif total_minutes >= 300:
            return {
                "name": "Rank D: 鉄の駆け出し",
                "color": "#708090",
                "next": 1200,
                "base": 300,
                "img": "rank_d.png",
            }
        else:
            return {
                "name": "Rank E: 見習い",
                "color": "#607D8B",
                "next": 300,
                "base": 0,
                "img": "rank_e.png",
            }

    @staticmethod
    def get_rank_info_by_char(rank_char):
        """ランク文字(S,A,B,C,D,E)からランク情報を取得"""
        rank_char = str(rank_char).upper().strip()
        if rank_char == "S":
            return {
                "name": "Rank S: 伝説の勇者",
                "color": "#9932CC",
                "img": "rank_s.png",
            }
        elif rank_char == "A":
            return {
                "name": "Rank A: 黄金の騎士",
                "color": "#FFD700",
                "img": "rank_a.png",
            }
        elif rank_char == "B":
            return {
                "name": "Rank B: 銀の熟練者",
                "color": "#C0C0C0",
                "img": "rank_b.png",
            }
        elif rank_char == "C":
            return {
                "name": "Rank C: 銅の戦士",
                "color": "#CD7F32",
                "img": "rank_c.png",
            }
        elif rank_char == "D":
            return {
                "name": "Rank D: 鉄の駆け出し",
                "color": "#708090",
                "img": "rank_d.png",
            }
        else:
            return {
                "name": "Rank E: 見習い",
                "color": "#607D8B",
                "img": "rank_e.png",
            }

    @staticmethod
    def create_medal_home_gui(user_data, weekly_ranking=[]):
        """勲章メインのホーム画面を生成"""
        total_minutes = int(user_data.get("total_study_time", 0))

        # 基本情報の計算（進捗バー計算用）
        rank_data = StatusService.get_rank_info(total_minutes)

        # usersシートのランク指定があれば、表示情報（名前・画像・色）を上書きする
        sheet_rank = user_data.get("rank")
        if sheet_rank:
            sheet_rank_info = StatusService.get_rank_info_by_char(sheet_rank)
            rank_data["name"] = sheet_rank_info["name"]
            rank_data["color"] = sheet_rank_info["color"]
            rank_data["img"] = sheet_rank_info["img"]

        import os

        app_url = os.environ.get("APP_URL", "https://your-app.herokuapp.com")
        if app_url.endswith("/"):
            app_url = app_url[:-1]
        img_url = f"{app_url}/static/medals/{rank_data['img']}"

        # 次のランクまでの計算
        if rank_data["next"]:
            needed = rank_data["next"] - total_minutes
            current_in_rank = total_minutes - rank_data["base"]
            total_in_rank = rank_data["next"] - rank_data["base"]
            progress_percent = int((current_in_rank / total_in_rank) * 100)
            needed_str = StatusService.format_duration(needed)
            next_text = f"あと {needed_str} で昇格"
        else:
            progress_percent = 100
            next_text = "最高ランク到達！"

        # 実績グリッドの生成
        achievements_str = str(user_data.get("unlocked_achievements", ""))
        achievements_grid = AchievementManager.generate_flex_component(achievements_str)

        # バッジ（勲章）の取得
        from services.economy import EconomyService

        badges = EconomyService.get_user_badges(str(user_data.get("user_id")))

        badge_contents = []
        if badges:
            for b in badges:
                badge_contents.append(
                    {
                        "type": "box",
                        "layout": "vertical",
                        "width": "60px",
                        "alignItems": "center",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "width": "40px",
                                "height": "40px",
                                "backgroundColor": "#FFD700",  # Gold background for badges
                                "cornerRadius": "50px",  # Circle
                                "justifyContent": "center",
                                "alignItems": "center",
                                "contents": [
                                    {"type": "text", "text": b["icon"], "size": "xl"}
                                ],
                            },
                            {
                                "type": "text",
                                "text": b["name"],
                                "size": "xxs",
                                "color": "#aaaaaa",
                                "align": "center",
                                "margin": "xs",
                                "wrap": True,
                            },
                        ],
                        "margin": "xs",
                    }
                )

        # ランキングセクションの構築
        ranking_contents = []
        if weekly_ranking:
            ranking_contents.append(
                {
                    "type": "text",
                    "text": "🏆 WEEKLY RANKING",
                    "color": "#FFD700",
                    "size": "xs",
                    "weight": "bold",
                    "margin": "lg",
                }
            )

            # Top 3
            for i, r in enumerate(weekly_ranking[:3]):
                is_me = str(r["user_id"]) == str(user_data["user_id"])
                color = "#ffffff" if is_me else "#aaaaaa"
                weight = "bold" if is_me else "regular"
                rank_icon = "👑" if i == 0 else f"{i + 1}."

                # ランク画像の取得
                user_rank_char = r.get("user_rank")
                if user_rank_char:
                    r_rank_info = StatusService.get_rank_info_by_char(user_rank_char)
                else:
                    r_total = int(r.get("total_study_time", 0))
                    r_rank_info = StatusService.get_rank_info(r_total)

                # ランクに応じたアイコン (E~S) を使用
                # すでに img プロパティが rank_a.png 等になっているが、
                # アイコンとして表示する場合は単純な文字や小さなアイコンの方が視認性が良い場合もある。
                # ここではユーザーのランクに応じた画像URLを使用する。
                r_img_url = f"{app_url}/static/medals/{r_rank_info['img']}"

                # ユーザー名の横に表示するテキスト勲章 (例: [S])
                rank_char = r_rank_info["name"].split(":")[0].replace("Rank ", "")
                rank_badge_text = f"[{rank_char}]"
                rank_badge_color = r_rank_info["color"]

                ranking_contents.append(
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "sm",
                        "alignItems": "center",
                        "contents": [
                            {
                                "type": "text",
                                "text": str(rank_icon),
                                "color": "#FFD700",
                                "size": "sm",
                                "flex": 1,
                                "align": "center",
                            },
                            {
                                "type": "image",
                                "url": r_img_url,
                                "size": "xs",
                                "aspectMode": "fit",
                                "flex": 1,
                            },
                            {
                                "type": "text",
                                "text": r["display_name"],
                                "color": color,
                                "size": "sm",
                                "flex": 4,
                                "weight": weight,
                                "margin": "sm",
                            },
                            {
                                "type": "text",
                                "text": f"{r['weekly_exp']}",
                                "color": color,
                                "size": "sm",
                                "flex": 2,
                                "align": "end",
                            },
                        ],
                    }
                )

            # 自分が3位以下の場合、自分の順位を表示
            my_rank_data = next(
                (
                    r
                    for r in weekly_ranking
                    if str(r["user_id"]) == str(user_data["user_id"])
                ),
                None,
            )
            if my_rank_data and my_rank_data["rank"] > 3:
                m_rank_char_val = my_rank_data.get("user_rank")
                if m_rank_char_val:
                    m_rank_info = StatusService.get_rank_info_by_char(m_rank_char_val)
                else:
                    m_total = int(my_rank_data.get("total_study_time", 0))
                    m_rank_info = StatusService.get_rank_info(m_total)
                
                m_img_url = f"{app_url}/static/medals/{m_rank_info['img']}"

                ranking_contents.append(
                    {"type": "separator", "margin": "sm", "color": "#444444"}
                )
                ranking_contents.append(
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "sm",
                        "alignItems": "center",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"{my_rank_data['rank']}.",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 1,
                                "align": "center",
                            },
                            {
                                "type": "image",
                                "url": m_img_url,
                                "size": "xs",
                                "aspectMode": "fit",
                                "flex": 1,
                            },
                            {
                                "type": "text",
                                "text": "You",
                                "color": "#ffffff",
                                "size": "sm",
                                "flex": 4,
                                "weight": "bold",
                                "margin": "sm",
                            },
                            {
                                "type": "text",
                                "text": f"{my_rank_data['weekly_exp']}",
                                "color": "#ffffff",
                                "size": "sm",
                                "flex": 2,
                                "align": "end",
                            },
                        ],
                    }
                )

        # Admin check
        is_admin = EconomyService.is_admin(str(user_data.get("user_id")))

        # フッターボタンの構築
        footer_contents = [
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "勉強",
                            "text": "勉強開始",
                        },
                        "color": "#4D96FF",
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "詳細",
                            "text": "詳細ステータス",
                        },
                        "color": "#FFD93D",
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "ガチャ",
                            "text": "ガチャ",
                        },
                        "color": "#FF6B6B",
                    },
                ],
            },
            # ショップとジョブは削除
        ]

        # 3段目: 履歴 | 切替 | (Adminのみ) 管理
        row3_contents = [
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "postback",
                    "label": "履歴",
                    "data": "action=show_history",
                },
            },
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "postback",
                    "label": "切替",
                    "data": "action=switch_user_menu",
                },
                "color": "#90A4AE",
            },
        ]

        if is_admin:
            row3_contents.append(
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "管理",
                        "text": "コマンド",
                    },
                    "color": "#333333",
                }
            )

        footer_contents.append(
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": row3_contents,
            }
        )

        bubble = {
            "type": "bubble",
            "size": "giga",
            "styles": {
                "header": {"backgroundColor": rank_data["color"]},
                "body": {"backgroundColor": "#202020"},
                "footer": {"backgroundColor": "#1a1a1a"},
            },
            "header": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "flex": 4,
                        "contents": [
                            {
                                "type": "text",
                                "text": "CURRENT RANK",
                                "color": "#888888",
                                "size": "xxs",
                                "weight": "bold",
                                "letterSpacing": "2px",
                            },
                            {
                                "type": "text",
                                "text": rank_data["name"],
                                "color": "#ffffff",
                                "size": "lg",
                                "weight": "bold",
                                "margin": "sm",
                            },
                        ],
                    },
                    {
                        "type": "image",
                        "url": img_url,
                        "flex": 2,
                        "size": "xl",
                        "aspectRatio": "1:1",
                        "aspectMode": "fit",
                        "align": "end",
                    },
                ],
            },
            "hero": {"type": "separator"},
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "NEXT RANK UP",
                        "color": "#aaaaaa",
                        "size": "xxs",
                        "margin": "md",
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "width": "100%",
                        "backgroundColor": "#444444",
                        "height": "4px",
                        "margin": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "width": f"{progress_percent}%",
                                "backgroundColor": rank_data["color"],
                                "height": "4px",
                            }
                        ],
                    },
                    {
                        "type": "text",
                        "text": next_text,
                        "color": "#ffffff",
                        "size": "xs",
                        "align": "end",
                        "margin": "sm",
                    },
                    # 実績表示エリア
                    {
                        "type": "text",
                        "text": "ACHIEVEMENTS",
                        "color": "#aaaaaa",
                        "size": "xxs",
                        "margin": "lg",
                    },
                    achievements_grid,
                    # バッジ表示エリア
                    *(
                        [
                            {
                                "type": "text",
                                "text": "SPECIAL BADGES",
                                "color": "#FFD700",
                                "size": "xxs",
                                "weight": "bold",
                                "margin": "lg",
                                "align": "center",
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": badge_contents,
                                "margin": "md",
                                "justifyContent": "center",
                                "wrap": True,
                            },
                        ]
                        if badge_contents
                        else []
                    ),
                    # ランキング表示エリア
                    {"type": "separator", "margin": "xxl", "color": "#444444"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": ranking_contents,
                        "margin": "lg",
                    },
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": footer_contents,
                "paddingTop": "20px",  # 上部に余白を追加して分離感を出す
                "paddingAll": "20px",
            },
        }

        return bubble

    @staticmethod
    def create_report_carousel(
        user_data, weekly_history, monthly_history, inventory_items
    ):
        """週間・月間レポートのカルーセルを生成"""

        # 週間レポートバブル
        weekly_bubble = StatusService._create_graph_bubble(
            "WEEKLY REPORT", user_data, weekly_history, inventory_items, is_weekly=True
        )

        # 月間レポートバブル
        monthly_bubble = StatusService._create_graph_bubble(
            "MONTHLY REPORT",
            user_data,
            monthly_history,
            None,  # 月間にはアイテム表示しない（スペース節約）
            is_weekly=False,
        )

        return {"type": "carousel", "contents": [weekly_bubble, monthly_bubble]}

    @staticmethod
    def _create_graph_bubble(
        title, user_data, history_data, inventory_items, is_weekly=True
    ):
        """グラフバブル生成の共通ロジック"""

        # 合計時間の計算
        total_min = int(sum([d["minutes"] for d in history_data]))

        # 最大値を求めてスケーリング (最低でも60分を最大とする)
        # 上部のテキストやレイアウト崩れを防ぐため、最大値を少し大きめ（1.25倍）に見積もる
        limit_val = 60
        # ガイドライン（3h, 6h, 9h, 12h）を考慮して、最大値がそれらを超える場合にスケール調整
        # しかしここでは単純に最大バーが天井につかないようにマージンを持たせる
        actual_max = max([d["minutes"] for d in history_data] + [limit_val])
        max_min = actual_max * 1.25

        # 科目別カラー定義
        subject_colors = {
            "国語": "#ff5555",  # Red
            "算数": "#5555ff",  # Blue
            "数学": "#5555ff",  # Blue
            "英語": "#ffd700",  # Yellow
            "理科": "#55ff55",  # Green
            "社会": "#ffa500",  # Orange
            "その他": "#aaaaaa",  # Gray
        }

        bars = []
        for day in history_data:
            total_minutes = day["minutes"]
            subjects = day.get("subjects", {})

            # 全体の高さ（最大値に対する割合）
            total_height_percent = int((total_minutes / max_min) * 100)
            if total_height_percent < 2 and total_minutes > 0:
                total_height_percent = 2

            # 積み上げバーの構成要素
            stack_contents = []
            if total_minutes > 0:
                for subj, mins in subjects.items():
                    if mins <= 0:
                        continue
                    ratio = int((mins / total_minutes) * 100)
                    if ratio < 1:
                        ratio = 1

                    color = subject_colors.get(subj, "#aaaaaa")

                    stack_contents.append(
                        {
                            "type": "box",
                            "layout": "vertical",
                            "width": "100%",
                            "height": f"{ratio}%",
                            "backgroundColor": color,
                        }
                    )
            else:
                stack_contents.append(
                    {
                        "type": "box",
                        "layout": "vertical",
                        "width": "100%",
                        "height": "100%",
                        "backgroundColor": "#333333",
                    }
                )
                total_height_percent = 2

            # ラベル処理
            label_text = day["label"]
            if is_weekly:
                # (月) -> 月
                if "(" in label_text:
                    label_text = label_text.split("(")[1][:-1]
            else:
                # 12/1~ -> 12/1
                label_text = label_text.replace("~", "")

            bars.append(
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 1,
                    "contents": [
                        {
                            "type": "text",
                            "text": StatusService.format_duration(total_minutes),
                            "size": "xxs",
                            "align": "center",
                            "color": "#ffffff",
                            "margin": "xs",
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "width": "12px",
                            "height": f"{total_height_percent}%",
                            "backgroundColor": "#333333"
                            if total_minutes == 0
                            else "#00000000",
                            "cornerRadius": "sm",
                            "margin": "xs",
                            "contents": stack_contents,
                        },
                        {
                            "type": "text",
                            "text": label_text,
                            "size": "xxs",
                            "align": "center",
                            "color": "#aaaaaa",
                            "margin": "xs",
                        },
                    ],
                    "alignItems": "center",
                    "justifyContent": "flex-end",
                }
            )

        # インベントリ（所持品）のカルーセル作成
        inventory_section = []
        if inventory_items is not None:
            inventory_bubbles = []
            if not inventory_items:
                inventory_bubbles.append(
                    {
                        "type": "text",
                        "text": "所持品はありません",
                        "color": "#aaaaaa",
                        "size": "xs",
                        "align": "center",
                    }
                )
            else:
                for item in inventory_items:
                    inventory_bubbles.append(
                        {
                            "type": "box",
                            "layout": "vertical",
                            "backgroundColor": "#333333",
                            "cornerRadius": "md",
                            "paddingAll": "sm",
                            "width": "80px",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": item.get("icon", "📦"),
                                    "size": "xl",
                                    "align": "center",
                                },
                                {
                                    "type": "text",
                                    "text": item.get("name", "Item"),
                                    "size": "xxs",
                                    "align": "center",
                                    "wrap": True,
                                    "margin": "sm",
                                    "color": "#ffffff",
                                },
                                {
                                    "type": "text",
                                    "text": f"x{item.get('count', 1)}",
                                    "size": "xs",
                                    "align": "center",
                                    "color": "#FFD700",
                                    "weight": "bold",
                                },
                            ],
                        }
                    )

            inventory_section = [
                {"type": "separator", "margin": "md", "color": "#444444"},
                {
                    "type": "text",
                    "text": "🎒 ITEMS",
                    "weight": "bold",
                    "size": "sm",
                    "margin": "md",
                    "color": "#aaaaaa",
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": inventory_bubbles,
                    "spacing": "sm",
                    "margin": "sm",
                },
            ]

        # 統計情報の生成
        # total_min = sum([d["minutes"] for d in history_data]) # define at top
        stats_section = []

        # 偏差値計算用の期間合計時間 (グラフの合計ではなく、カレンダー基準の正しい集計値を使う)
        calc_min = 0
        if is_weekly:
            calc_min = int(user_data.get("weekly_study_time", 0))
        else:
            calc_min = int(user_data.get("monthly_study_time", 0))

        if calc_min > 0:
            if is_weekly:
                stats = SagaStats.calculate_weekly(calc_min)
                period_label = "週間偏差値"
            else:
                stats = SagaStats.calculate_monthly(calc_min)
                period_label = "月間偏差値"

            if stats:
                school_color = "#FFD700" if stats["is_saganishi"] else "#ffffff"
                stats_section = [
                    {"type": "separator", "margin": "md", "color": "#444444"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "md",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📊 佐賀県統計モデル",
                                "size": "xxs",
                                "color": "#aaaaaa",
                                "weight": "bold",
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": f"{period_label}: {stats['deviation']}",
                                        "size": "sm",
                                        "color": "#ffffff",
                                    },
                                    {
                                        "type": "text",
                                        "text": stats["school_level"],
                                        "size": "sm",
                                        "color": school_color,
                                        "align": "end",
                                        "weight": "bold",
                                    },
                                ],
                            },
                        ],
                    },
                ]

        bubble = {
            "type": "bubble",
            "size": "mega",
            "styles": {
                "header": {"backgroundColor": "#1a1a1a"},
                "body": {"backgroundColor": "#202020"},
                "footer": {"backgroundColor": "#1a1a1a"},
            },
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "color": "#888888",
                        "size": "xxs",
                        "weight": "bold",
                        "letterSpacing": "2px",
                    },
                    {
                        "type": "text",
                        "text": f"{user_data['display_name']}の学習記録",
                        "color": "#ffffff",
                        "size": "xs",
                        "weight": "bold",
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "text",
                                "text": StatusService.format_duration(total_min),
                                "color": "#ffffff",
                                "size": "4xl",
                                "weight": "bold",
                                "flex": 0,
                            },
                        ],
                        "justifyContent": "center",
                    },
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "height": "150px",
                        "contents": bars,
                        "alignItems": "flex-end",
                    },
                    {"type": "separator", "margin": "md", "color": "#444444"},
                ]
                + stats_section
                + inventory_section,
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "📊 詳細レポート (Looker)",
                            "uri": "https://lookerstudio.google.com/",
                        },
                        "style": "primary",
                        "color": "#4285F4",
                    }
                ],
            },
        }
        return bubble

    @staticmethod
    def create_weekly_graph_gui(user_data, weekly_history, inventory_items):
        """週間学習記録の棒グラフ画面を生成（積み上げグラフ）"""
        return StatusService._create_graph_bubble(
            "WEEKLY REPORT", user_data, weekly_history, inventory_items, is_weekly=True
        )
