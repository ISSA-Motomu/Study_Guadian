import urllib.parse
import json


class StatusService:
    @staticmethod
    def get_rank_info(total_minutes):
        """累計勉強時間からランク情報を取得"""
        # ランク定義
        # E: 0-180, D: 180-600, C: 600-1200, B: 1200-3000, A: 3000-6000, S: 6000+
        if total_minutes >= 6000:
            return {
                "name": "Rank S: 伝説の勇者",
                "color": "#9932CC",
                "next": None,
                "base": 6000,
                "img": "rank_s.png",
            }
        elif total_minutes >= 3000:
            return {
                "name": "Rank A: 黄金の騎士",
                "color": "#FFD700",
                "next": 6000,
                "base": 3000,
                "img": "rank_a.png",
            }
        elif total_minutes >= 1200:
            return {
                "name": "Rank B: 銀の熟練者",
                "color": "#C0C0C0",
                "next": 3000,
                "base": 1200,
                "img": "rank_b.png",
            }
        elif total_minutes >= 600:
            return {
                "name": "Rank C: 銅の戦士",
                "color": "#CD7F32",
                "next": 1200,
                "base": 600,
                "img": "rank_c.png",
            }
        elif total_minutes >= 180:
            return {
                "name": "Rank D: 鉄の駆け出し",
                "color": "#708090",
                "next": 600,
                "base": 180,
                "img": "rank_d.png",
            }
        else:
            return {
                "name": "Rank E: 見習い",
                "color": "#A9A9A9",
                "next": 180,
                "base": 0,
                "img": "rank_e.png",
            }

    @staticmethod
    def create_medal_home_gui(user_data, weekly_ranking=[]):
        """勲章メインのホーム画面を生成"""
        total_minutes = int(user_data.get("total_study_time", 0))

        rank_data = StatusService.get_rank_info(total_minutes)

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
            next_text = f"あと {needed}分 で昇格"
        else:
            progress_percent = 100
            next_text = "最高ランク到達！"

        # リボン（スキル）の判定
        ribbons = []
        # 赤リボン: 早起き
        ribbons.append({"color": "#ff5555", "text": "早起き", "icon": "⏰"})
        # 青リボン: 家事 (ジョブ数 > 10)
        if int(user_data.get("total_jobs", 0)) >= 10:
            ribbons.append({"color": "#5555ff", "text": "家事王", "icon": "🧹"})
        # 緑リボン: 継続 (仮)
        ribbons.append({"color": "#55ff55", "text": "継続", "icon": "🔥"})

        ribbon_contents = []
        for r in ribbons:
            ribbon_contents.append(
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
                            "backgroundColor": r["color"],
                            "cornerRadius": "md",
                            "justifyContent": "center",
                            "alignItems": "center",
                            "contents": [
                                {"type": "text", "text": r["icon"], "size": "xl"}
                            ],
                        },
                        {
                            "type": "text",
                            "text": r["text"],
                            "size": "xxs",
                            "color": "#aaaaaa",
                            "align": "center",
                            "margin": "xs",
                        },
                    ],
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

                ranking_contents.append(
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "sm",
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
                                "type": "text",
                                "text": r["display_name"],
                                "color": color,
                                "size": "sm",
                                "flex": 4,
                                "weight": weight,
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
                ranking_contents.append(
                    {"type": "separator", "margin": "sm", "color": "#444444"}
                )
                ranking_contents.append(
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "sm",
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
                                "type": "text",
                                "text": "You",
                                "color": "#ffffff",
                                "size": "sm",
                                "flex": 4,
                                "weight": "bold",
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

        bubble = {
            "type": "bubble",
            "size": "giga",
            "styles": {
                "header": {"backgroundColor": "#1a1a1a"},
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
                                "color": rank_data["color"],
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
                        "size": "lg",
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
                    # リボン表示エリア
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": ribbon_contents,
                        "margin": "lg",
                        "justifyContent": "center",
                    },
                    # ランキング表示エリア
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": ranking_contents,
                        "margin": "md",
                    },
                ],
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#bbbbbb",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "勉強する",
                            "text": "勉強開始",
                        },
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "データ",
                            "text": "詳細ステータス",
                        },
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#ff5555",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "ガチャ",
                            "text": "ガチャ",
                        },
                    },
                ],
            },
        }
        return bubble

    @staticmethod
    def create_weekly_graph_gui(user_data, weekly_history, inventory_items):
        """週間学習記録の棒グラフ画面を生成"""

        # 最大値を求めてスケーリング (最低でも60分を最大とする)
        max_min = max([d["minutes"] for d in weekly_history] + [60])

        bars = []
        for day in weekly_history:
            minutes = day["minutes"]
            height_percent = int((minutes / max_min) * 100)
            if height_percent < 1:
                height_percent = 1  # 最低1%

            # 棒の色 (勉強した日は青、0はグレー)
            bar_color = "#5555ff" if minutes > 0 else "#333333"

            bars.append(
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 1,
                    "contents": [
                        {
                            "type": "text",
                            "text": str(minutes),
                            "size": "xxs",
                            "align": "center",
                            "color": "#ffffff",
                            "margin": "xs",
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "width": "12px",
                            "height": f"{height_percent}%",
                            "backgroundColor": bar_color,
                            "cornerRadius": "sm",
                            "margin": "xs",
                        },
                        {
                            "type": "text",
                            "text": day["label"].split("(")[1][:-1],  # (月) -> 月
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
                        "text": "WEEKLY REPORT",
                        "color": "#888888",
                        "size": "xxs",
                        "weight": "bold",
                        "letterSpacing": "2px",
                    },
                    {
                        "type": "text",
                        "text": f"{user_data['display_name']}の学習記録",
                        "color": "#ffffff",
                        "size": "md",
                        "weight": "bold",
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
                    {
                        "type": "text",
                        "text": f"Total: {sum([d['minutes'] for d in weekly_history])} min",
                        "size": "sm",
                        "color": "#ffffff",
                        "align": "end",
                        "margin": "md",
                    },
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
                ],
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "message",
                            "label": "🎲 ガチャ",
                            "text": "ガチャ",
                        },
                        "style": "primary",
                        "color": "#ff5555",
                    }
                ],
            },
        }
        return bubble
