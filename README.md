
## 🛠️ 技術スタック

- **Language**: Python 3.11
- **Framework**: Flask
- **Platform**: LINE Messaging API (Flex Message)
- **Database**: Google Sheets (gspread)
- **Hosting**: Render
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
│   └── admin.py          # 管理者コマンド
│   └── ...
├── services/             # ビジネスロジック
│   ├── gsheet.py         # Google Sheets連携
│   ├── history.py        # 履歴・統計取得
│   ├── status_service.py # 画像生成・UI構築ロジック
│   └── stats.py          # 統計計算ロジック
├── templates/            # LINE Flex Message JSONテンプレート
└── static/               # 静的ファイル (画像など)
```

## ⚙️ 環境変数 (.env)

- `CHANNEL_ACCESS_TOKEN`: LINE Messaging API トークン
- `CHANNEL_SECRET`: LINE Messaging API シークレット
- `GOOGLE_SHEET_KEY`: データベース用スプレッドシートID
- `GOOGLE_CREDENTIALS_JSON`: Google Service Account JSON
- `APP_URL`: アプリの公開URL (画像配信等に使用)


