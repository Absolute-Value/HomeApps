# 家計簿アプリ

## How To Use

### dockerを導入済みの場合

docker composeを使用してコンテナを起動
```bash
docker compose up -d
```

### 開発用
```bash
sudo docker compose down --volumes --remove-orphans --rmi all && sudo docker compose up --build -d
```