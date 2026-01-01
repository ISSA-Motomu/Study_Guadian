# Study_Guadian
- 6人子供の長男として家庭環境の改造を目指す
- LINE Botを作ってみる

# ディレクトリ構造
```
Study-Guardian/
├── .env                  # 環境変数
├── .gitignore
├── requirements.txt
├── Procfile              # Render起動用
├── app.py                # エントリーポイント（ルーティングのみ）
├── services/             # 具体的な処理ロジックを入れる場所
│   ├── __init__.py
│   ├── line_bot.py       # LINE Botのメッセージ処理・返信機能
│   ├── gsheet.py         # スプレッドシートの読み書き機能
│   ├── statistics.py     # 佐賀県統計・偏差値計算機能
│   └── game_system.py    # EX計算・通貨換算機能
└── utils/                # 便利ツール（日付計算など）
    ├── __init__.py
    └── time_calc.py
```

# **開発環境**
  - Python
  - Render
  - Google API
  - Line Official Account
