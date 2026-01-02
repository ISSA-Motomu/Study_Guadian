import random
from linebot.models import FlexSendMessage, TextSendMessage
from bot_instance import line_bot_api
from services.economy import EconomyService


def handle_message(event, text):
    user_id = event.source.user_id

    if text == "ガチャ":
        # 1. コスト確認
        COST = 500
        if not EconomyService.check_balance(user_id, COST):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"EXPが足りません。\nガチャを引くには {COST} EXP必要です。"
                ),
            )
            return True

        # 2. EXP消費
        EconomyService.add_exp(user_id, -COST, related_id="GACHA_PLAY")

        # 3. 抽選ロジック
        # SSR: 5%, SR: 10%, R: 30%, C: 55%
        rand = random.random() * 100
        if rand < 5:
            item = {
                "key": "ticket_1.5x",
                "name": "EXP 1.5倍チケット",
                "rarity": "SSR",
                "color": "#FFD700",
                "icon": "🎟",
            }
        elif rand < 15:
            item = {
                "key": "shield_chores",
                "name": "絶対防御 (家事免除)",
                "rarity": "SR",
                "color": "#C0C0C0",
                "icon": "🛡",
            }
        elif rand < 45:
            item = {
                "key": "bonus_100",
                "name": "臨時ボーナス (100EXP)",
                "rarity": "R",
                "color": "#CD7F32",
                "icon": "💸",
            }
        else:
            item = {
                "key": "supple_focus",
                "name": "集中サプリ",
                "rarity": "C",
                "color": "#A9A9A9",
                "icon": "💊",
            }

        # 4. アイテム付与
        EconomyService.add_inventory_item(user_id, item["key"])

        # ボーナスアイテムの場合は即時EXP付与
        if item["key"] == "bonus_100":
            EconomyService.add_exp(user_id, 100, related_id="GACHA_BONUS")

        # 5. 結果表示 (Flex Message)
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "GACHA RESULT",
                        "weight": "bold",
                        "color": "#1DB446",
                        "size": "sm",
                    },
                    {
                        "type": "text",
                        "text": item["rarity"],
                        "weight": "bold",
                        "size": "3xl",
                        "margin": "md",
                        "color": item["color"],
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": item["icon"],
                        "size": "5xl",
                        "align": "center",
                        "margin": "lg",
                    },
                    {
                        "type": "text",
                        "text": item["name"],
                        "weight": "bold",
                        "size": "xl",
                        "margin": "lg",
                        "align": "center",
                        "wrap": True,
                    },
                    {"type": "separator", "margin": "xl"},
                    {
                        "type": "text",
                        "text": f"消費: {COST} EXP",
                        "size": "xs",
                        "color": "#aaaaaa",
                        "margin": "md",
                        "align": "center",
                    },
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "message",
                            "label": "もう一度引く",
                            "text": "ガチャ",
                        },
                        "style": "primary",
                        "color": "#ff5555",
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "message",
                            "label": "閉じる",
                            "text": "ステータス",
                        },
                        "margin": "sm",
                    },
                ],
            },
        }

        line_bot_api.reply_message(
            event.reply_token, FlexSendMessage(alt_text="ガチャ結果", contents=bubble)
        )
        return True

    return False
