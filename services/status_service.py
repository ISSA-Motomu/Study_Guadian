import urllib.parse
import json


class StatusService:
    @staticmethod
    def create_medal_home_gui(user_data):
        """勲章メインのホーム画面を生成"""
        total_minutes = int(user_data.get("total_study_time", 0))

        # ランク定義
        # E: 0-180, D: 180-600, C: 600-1200, B: 1200-3000, A: 3000-6000, S: 6000+
        if total_minutes >= 6000:
            rank_data = {
                "name": "Rank S: 伝説の勇者",
                "color": "#9932CC",
                "next": None,
                "base": 6000,
                "img": "rank_s.png",
            }
        elif total_minutes >= 3000:
            rank_data = {
                "name": "Rank A: 黄金の騎士",
                "color": "#FFD700",
                "next": 6000,
                "base": 3000,
                "img": "rank_a.png",
            }
        elif total_minutes >= 1200:
            rank_data = {
                "name": "Rank B: 銀の熟練者",
                "color": "#C0C0C0",
                "next": 3000,
                "base": 1200,
                "img": "rank_b.png",
            }
        elif total_minutes >= 600:
            rank_data = {
                "name": "Rank C: 銅の戦士",
                "color": "#CD7F32",
                "next": 1200,
                "base": 600,
                "img": "rank_c.png",
            }
        elif total_minutes >= 180:
            rank_data = {
                "name": "Rank D: 鉄の駆け出し",
                "color": "#708090",
                "next": 600,
                "base": 180,
                "img": "rank_d.png",
            }
        else:
            rank_data = {
                "name": "Rank E: 見習い",
                "color": "#A9A9A9",
                "next": 180,
                "base": 0,
                "img": "rank_e.png",
            }

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
                            "margin": "auto",
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
                        "flex": 1,
                        "size": "xs",
                        "aspectRatio": "1:1",
                        "aspectMode": "fit",
                        "align": "end",
                    },
                ],
            },
            "hero": {
                "type": "box",
                "layout": "vertical",
                "contents": [],
                "height": "1px",
            },
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
    def create_life_skills_gui(user_data, inventory_items):
        # 1. パラメータ計算
        # user_data keys: user_id, display_name, current_exp, total_study_time, role, inventory_json

        total_study_time = int(user_data.get("total_study_time", 0))
        current_exp = int(user_data.get("current_exp", 0))

        # 仮のロジック
        stats = {
            "知力": min(100, int(total_study_time / 10)),  # 1000分でMAX
            "労働": min(100, int(current_exp / 50)),  # 仮: EXPを労働の代替指標に
            "資産": min(100, int(current_exp / 100)),  # EXPが資産
            "規律": 80,  # 仮
            "運": 50,  # 仮
        }

        # 2. レーダーチャート画像のURL生成 (QuickChart API)
        chart_config = {
            "type": "radar",
            "data": {
                "labels": ["Brain", "Labor", "Cash", "Rule", "Luck"],
                "datasets": [
                    {
                        "label": "User Stats",
                        "data": [
                            stats["知力"],
                            stats["労働"],
                            stats["資産"],
                            stats["規律"],
                            stats["運"],
                        ],
                        "backgroundColor": "rgba(39, 172, 178, 0.5)",
                        "borderColor": "#27ACB2",
                        "pointBackgroundColor": "#fff",
                    }
                ],
            },
            "options": {
                "scale": {"ticks": {"min": 0, "max": 100, "display": False}},
                "legend": {"display": False},
            },
        }

        chart_url = "https://quickchart.io/chart?c=" + urllib.parse.quote(
            json.dumps(chart_config)
        )

        # 3. インベントリ（所持品）のカルーセル作成
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
                # item structure: {"name": "...", "icon": "...", "count": 1}
                inventory_bubbles.append(
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#f0f0f0",
                        "cornerRadius": "md",
                        "paddingAll": "md",
                        "width": "80px",
                        "contents": [
                            {
                                "type": "text",
                                "text": item.get("icon", "📦"),
                                "size": "xxl",
                                "align": "center",
                            },
                            {
                                "type": "text",
                                "text": item.get("name", "Item"),
                                "size": "xxs",
                                "align": "center",
                                "wrap": True,
                                "margin": "sm",
                            },
                            {
                                "type": "text",
                                "text": f"x{item.get('count', 1)}",
                                "size": "xs",
                                "align": "center",
                                "color": "#27ACB2",
                                "weight": "bold",
                            },
                        ],
                    }
                )

        # 4. Flex Message 全体構築
        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "LIFE SKILLS",
                        "weight": "bold",
                        "color": "#27ACB2",
                        "size": "sm",
                    },
                    {
                        "type": "text",
                        "text": f"{user_data.get('display_name')} の生活力",
                        "weight": "bold",
                        "size": "xl",
                    },
                ],
            },
            "hero": {
                "type": "image",
                "url": chart_url,
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "cover",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "separator", "margin": "md"},
                    {
                        "type": "text",
                        "text": "🎒 ITEMS",
                        "weight": "bold",
                        "size": "sm",
                        "margin": "md",
                        "color": "#555555",
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
