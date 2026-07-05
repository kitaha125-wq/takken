# 宅建士合格アプリ

## ⚠️ Netlify が iPhone で開けないとき

**原因：** Netlify はまだ古い版のまま。スマホでは起動できません。  
**解決：** 1回だけ更新すれば、同じ URL で開けます（データは残ります）。

👉 **手順ページ（iPhoneで開く）：**  
**https://kitaha125-wq.github.io/takken/netlify-fix.html**

### いちばん簡単な更新（Git連携・1回だけ）

1. https://app.netlify.com にログイン
2. サイト **classy-kleicha-030356** → **Site configuration** → **Build & deploy**
3. **Link repository** → GitHub → **kitaha125-wq/takken** → branch **main** → Deploy
4. 3分後に https://classy-kleicha-030356.netlify.app/index.html を開く

---

## いちばん簡単：URLを開くだけ（ダウンロード不要）

### スマホで開けないとき（まずここ）

**https://kitaha125-wq.github.io/takken/start.html**（接続テスト・すぐ開く）

**https://kitaha125-wq.github.io/takken/restore.html**（バックアップ復元だけ・すぐ開く）

### メインアプリ（2.4MB・初回2〜4分かかることがある）

**https://classy-kleicha-030356.netlify.app/index.html**（いつものURL・データあり）

**https://kitaha125-wq.github.io/takken/index.html**（更新版）

Safari で開く → ホーム画面に追加

---

## Netlify を更新する（3つの方法）

### 方法A：Git 連携（おすすめ・ファイル不要）

1. https://app.netlify.com/ にログイン
2. **Add new site** → **Import an existing project**
3. **GitHub** → リポジトリ `kitaha125-wq/takken` を選択
4. 設定はそのまま **Deploy site**
5. 以降、`main` を更新するたびに自動デプロイ

※ 既存サイト `classy-kleicha-030356` がある場合：
- そのサイトの **Site configuration** → **Build & deploy** → **Link repository**
- 同じ `takken` リポジトリを選ぶ

---

### 方法B：ZIP をダウンロード（PDFにならない）

1. iPhone/Mac の Safari で次を開く：

   **https://github.com/kitaha125-wq/takken/releases/latest**

2. **takken-app-update.zip** をタップしてダウンロード
3. ZIP を解凍 → 中の `index.html` が出る
4. Netlify → サイト → **Deploys** → `index.html` をドラッグ＆ドロップ

⚠️ GitHub のページで「共有→PDF」は使わないでください（PDFになります）

---

### 方法C：Mac のターミナル（上級者）

```bash
cd ~/Downloads
curl -L -o index.html https://github.com/kitaha125-wq/takken/raw/main/index.html
```

Netlify の Deploys に `index.html` をドロップ

---

## 更新できたか確認

問題集を開始して、次が表示されれば成功：

- **わからない（スキップ →）**
- **✏️ 問題を修正**

## 進捗データの引き継ぎ

URL を変える場合は、旧アプリで **💾 バックアップをダウンロード** → 新URLで **復元**
