
# Study Guardian

学習習慣を楽しく身につけるためのLINE Bot & LIFFアプリケーションです。
勉強時間を記録し、RPGのようにレベルアップやコイン獲得ができるゲーミフィケーション要素を取り入れています。

## 🌟 主な機能

- **学習タイマー**:
  - 科目を選択して勉強時間を計測
  - ストップウォッチ形式で経過時間を表示
  - 勉強終了時にメモを残せる機能
- **ゲーミフィケーション**:
  - 勉強時間に応じてEXP（経験値）とコインを獲得
  - レベルアップ機能とランクシステム
- **可視化**:
  - 週間学習グラフ（LIFF上で確認可能）
- **快適なUX**:
  - 効果音（起動音、選択音、レベルアップ音）によるフィードバック
  - 直感的なカード型UI

## 🛠️ 技術スタック

- **Language**: Python 3.11
- **Framework**: Flask
- **Platform**: LINE Messaging API (Flex Message)
- **Database**: Google Sheets (gspread)
- **Hosting**: Render / Heroku
- **Visualization**: Looker Studio (optional)

## 📂 ディレクトリ構造

```text
Study_Guadian/
├── app.py                # アプリケーションエントリーポイント
├── bot_instance.py       # LINE Bot API初期化
├── handlers/             # LINEイベントハンドラ (機能別)
│   ├── study.py          # 勉強関連
│   ├── job.py            # ジョブ関連
│   ├── shop.py           # ショップ関連
│   ├── status.py         # ステータス・ランキング
│   ├── admin.py          # 管理者コマンド
│   ├── help.py           # ヘルプ・ガイド
│   ├── common.py         # 共通処理・ユーザー管理
│   └── ...
├── services/             # ビジネスロジック
│   ├── gsheet.py         # Google Sheets連携
│   ├── history.py        # 履歴・統計取得
│   ├── status_service.py # 画像生成・UI構築ロジック
│   ├── economy.py        # 経済システム・権限管理
│   └── stats.py          # 統計計算ロジック
├── templates/            # LINE Flex Message JSONテンプレート
├── static/               # 静的ファイル (画像など)
└── docs/                 # ドキュメント
    └── command.md        # コマンド一覧
```

## ⚙️ 環境変数 (.env)

- `LINE_CHANNEL_ACCESS_TOKEN`: LINE Messaging API トークン
- `LINE_CHANNEL_SECRET`: LINE Messaging API シークレット
- `SPREADSHEET_ID`: データベース用スプレッドシートID
- `GOOGLE_CREDENTIALS`: Google Service Account JSON
- `APP_URL`: アプリの公開URL (画像配信等に使用)


