# チャットボット+家計簿アプリ

## How To Use

### dockerを導入済みの場合

.envファイルにOPENAI_API_KEYとOPENAI_API_VERSIONを設定
```bash
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_VERSION=2025-01-01-preview
```

ログイン用のユーザー名とパスワードの設定
```
sudo apt install apache2-utils -y
htpasswd -c ./nginx/.htpasswd your_username
```

1. 初回ビルド（イメージ作成）
```bash
sudo docker compose build
```

2. 初回のみ：Let's Encryptの証明書取得（HTTP経由）
以下のサーバーをコメントアウト
```
#  server {
#    listen 443 ssl;
```

nginxを再起動
```shell
sudo docker compose restart nginx
```

```bash
sudo docker compose run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --email clcl@f5.si \
  --agree-tos --no-eff-email \
  -d jky-home.ddns.net
```

コメントアウトを戻して、nginxを再起動
```shell
sudo docker compose restart nginx
```

3. コンテナの起動（HTTPSでStreamlitを公開）
```bash
sudo docker compose up -d
```

### 証明書の更新（90日ごと推奨）
Let's Encryptの証明書は有効期限が90日なので、更新が必要です。

```bash
sudo docker compose run --rm certbot renew
sudo docker compose exec nginx nginx -s reload
```

### 開発用
```bash
sudo docker compose down --volumes --remove-orphans --rmi all && sudo docker compose up --build -d
```
