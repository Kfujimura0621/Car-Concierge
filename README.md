# Car Concierge

中古車販売価格推定・車両データ管理システム

## 主な機能

- 中古車販売価格の推定
- 車種別の価格分析
- 車両データの検索・管理
- 管理者による車両登録
- 管理者・一般ユーザーの権限管理
- Argon2idによるパスワード保護
- ログイン回数制限
- 認証ログの記録

## 使用技術

- Python
- Streamlit
- Pandas / NumPy
- SQLite
- Argon2
- Ubuntu / systemd
- Cloudflare Tunnel

## セキュリティ

認証データベース、実車両データ、ログ、
認証情報はリポジトリに含めない。

## 開発予定

- PostgreSQLへの移行
- Dockerコンテナ化
- Zabbixによる監視
- 障害検知・自動復旧
- LINEによる障害通知
- Kubernetes / K3sへの対応

## 注意事項

本システムは開発・検証段階です。
推定価格の正確性を保証するものではありません。
