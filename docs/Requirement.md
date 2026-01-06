# データ構造定義 (Google Spreadsheets)

本システムでは、以下のシートを使用します。
各シートは **1行目がヘッダー（列キー）**、**2行目以降がデータ行（1行1レコード）** となるデータベース形式の構造です。

### Sheet 1: `users` (ユーザー管理)
| 列 | キー (Header) | 型 | 説明 | 例 |
|:---|:---|:---|:---|:---|
| A | user_id | String | LINE User ID | U1234abcd... |
| B | display_name | String | 表示名 | 次男 |
| C | current_exp | Integer | 所持EXP (残高) | 1500 |
| D | total_study_time | Integer | 累計勉強時間(分) | 1200 |
| E | role | String | 権限 (ADMIN/USER) | USER |
| F | inventory_json | JSON | 所持アイテム・勲章 | {"ticket_1.5x": 1} |
| G | rank | String | ランク (S-E) | A |

### Sheet 2: `study_log` (学習記録)
| 列 | キー (Header) | 型 | 説明 | 例 |
|:---|:---|:---|:---|:---|
| A | user_id | String | LINE User ID | U1234abcd... |
| B | user_name | String | 名前 (Snapshot) | 次男 |
| C | date | Date | 日付 | 2026-01-01 |
| D | start_time | Time | 開始時刻 | 18:30:00 |
| E | end_time | Time | 終了時刻 | 19:30:00 |
| F | status | String | 状態 (STARTED/PENDING/APPROVED/REJECTED/CANCELLED) | APPROVED |
| G | duration | Integer | 勉強時間(分) | 60 |
| H | rank | String | その時点のランク | B |
| I | subject | String | 科目 | 数学 |
| J | comment | String | 成果コメント | ドリルP20 |
| K | concentration | Integer | 集中度(1-5) | 5 |

### Sheet 3: `shop_items` (商品マスタ)
| 列 | キー (Header) | 型 | 説明 | 例 |
|:---|:---|:---|:---|:---|
| A | item_key | String | 商品ID (Unique) | game_30 |
| B | name | String | 商品名 | 🎮 ゲーム30分 |
| C | cost | Integer | 価格 (EXP) | 300 |
| D | description | String | 詳細説明 | Switch利用可 |
| E | is_active | Boolean | 有効フラグ | TRUE |

### Sheet 4: `shop_requests` (購入リクエスト)
| 列 | キー (Header) | 型 | 説明 | 例 |
|:---|:---|:---|:---|:---|
| A | request_id | String | リクエストID | req_1700000000 |
| B | user_id | String | LINE User ID | U1234... |
| C | item_key | String | 商品ID | game_30 |
| D | cost | Integer | 消費ポイント | 300 |
| E | status | String | 状態 (PENDING/APPROVED/DENIED) | PENDING |
| F | created_at | Datetime | 申請日時 | 2026-01-01 12:00:00 |
| G | comment | String | 用途コメント | マリオやる |

### Sheet 5: `transactions` (取引履歴)
| 列 | キー (Header) | 型 | 説明 | 例 |
|:---|:---|:---|:---|:---|
| A | tx_id | String | 取引ID | tx_001 |
| B | user_id | String | LINE User ID | U1234... |
| C | amount | Integer | 変動額 (+/-) | -300 |
| D | tx_type | String | 取引種別 (REWARD/SPEND/REFUND等) | SPEND |
| E | related_id | String | 関連ID (Job/Item/Grant) | game_30 |
| F | timestamp | Datetime | 発生日時 | 2026-01-01 12:00:00 |
| G | user_name | String | 名前 (Snapshot) | 次男 |

### Sheet 6: `jobs` (お手伝いタスク)
| 列 | キー (Header) | 型 | 説明 | 例 |
|:---|:---|:---|:---|:---|
| A | job_id | String | 求人ID | job_001 |
| B | title | String | タスク名 | 風呂掃除 |
| C | reward | Integer | 報酬 (EXP) | 300 |
| D | status | String | 状態 (OPEN/ASSIGNED/CLOSED) | OPEN |
| E | client_id | String | 依頼者(親)ID | U9999... |
| F | worker_id | String | 作業者(子)ID | U1234... |
| G | deadline | Date | 期限 | 2026-01-10 |

### Sheet 7: `missions` (ミッション/クエスト)
| 列 | キー (Header) | 型 | 説明 | 例 |
|:---|:---|:---|:---|:---|
| A | mission_id | String | ミッションID | msn_1700000000 |
| B | user_id | String | 対象ユーザーID | U1234... |
| C | title | String | タイトル | 計算ドリル完走 |
| D | description | String | 詳細 | 全部終わらせる |
| E | reward | Integer | 報酬 (EXP) | 500 |
| F | status | String | 状態 (OPEN/COMPLETED) | OPEN |
| G | created_at | Datetime | 作成日時 | 2026-01-01 10:00:00 |
| H | completed_at | Datetime | 完了日時 | 2026-01-05 18:00:00 |