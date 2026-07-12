# fukusiyougu（補装具・日常生活用具ナビ）

障害福祉サービスの「補装具」「日常生活用具」の更新時期（再支給が可能になる時期）を
管理する無料ツールと、用具の選び方・制度解説記事をまとめたサイトです。

設計書：`補装具_日常生活用具_更新管理ナビ_設計書.md`（別途共有済み）を参照してください。

---

## 構成（YAMLファイル以外はすべてルート直下に配置）

```
fukusiyougu/
├── .github/workflows/deploy.yml   … GitHub Actions（手動デプロイ、GitHubの仕様上このパス固定）
├── build.py                        … distフォルダを生成するビルドスクリプト
├── content_data.py                 … 用具マスタデータ＋記事コンテンツ（1ファイルに統合）
├── style.css                       … サイト全体のスタイル
├── script.js                       … ツールのロジック（日付計算・localStorage等）
├── wrangler.json                   … Cloudflare Worker設定
├── test_node.js                    … Node.js(jsdom)による動作検証スクリプト
├── package.json                    … 動作検証用の依存関係（jsdom）定義
├── .gitignore
└── dist/                            … build.py 実行後に生成される公開用フォルダ（Git管理対象外）
```

`build_src/` や `static/` のようなサブフォルダは作らず、ビルド関連ファイルは
すべてルート直下に置く構成にしています（GitHub Actionsの仕様上必須の
`.github/workflows/` のみ例外です）。

## ローカルでの動作確認

Python 3.9以上があれば、追加ライブラリのインストールなしで動作します。

```bash
python build.py
```

`dist/` フォルダが生成されるので、ローカルサーバーで確認してください。

```bash
cd dist
python -m http.server 8000
# ブラウザで http://localhost:8000 を開く
```

## Node.js(jsdom)での動作検証

```bash
npm install
npm test
```

日付計算ロジック（うるう年をまたぐケース等の境界値）や、登録・削除・
ダッシュボード集計・バリデーションの動作を自動テストで確認できます。

## デプロイ手順（GitHub Actions経由）

1. このリポジトリに `CLOUDFLARE_API_TOKEN` をSecretsとして登録する
   （GitHubリポジトリ → Settings → Secrets and variables → Actions）
2. Cloudflareダッシュボードで、`wrangler.json` の `name` と同じ名前のWorkerが
   作成される（初回デプロイ時に自動作成されます）
3. GitHubリポジトリの「Actions」タブ → 「Deploy to Cloudflare Workers」→
   「Run workflow」を手動実行する
4. デプロイ完了後、Cloudflareダッシュボードの「Workers & Pages」→ 該当Worker →
   「ドメイン」タブから、Custom Domain（例：`hosogu-navi.pray-power-is-god-and-cocoro.com`）
   を追加する

※ ロリポップ・`.htaccess`・`index.php` は不要です（Custom Domain方式のため）。

## トップページの背景デザインについて

トップページのヒーローセクションには、太陽・白い雲・アーチ状の虹を背景に、
車椅子・歩行補助つえ・歩行器・特殊寝台の簡易アイコンがふわふわと浮かぶ
インラインSVGを実装しています（`build.py` の `build_index()` 関数内）。
アイコンはCSSアニメーション（`style.css` の `.float-icon` 関連クラス）で
ゆっくり上下に揺れる演出にしています。`prefers-reduced-motion` 設定がある
環境では、アニメーションを自動的に停止します。

## 公開前チェックリスト（重要）

- [ ] `build.py` 冒頭の `NOINDEX = True` を確認する（**完成するまでは必ず True のまま**）
- [ ] `build.py` の `SITE_URL` を、実際に取得したCustom Domainに書き換える
- [ ] `npm test` で、フォーム送信・削除・並び替え・耐用年数判定ロジックを
      実際に動かして検証する（境界値：交付決定日が今日の場合、うるう年をまたぐ場合等）
- [ ] 記事内容（耐用年数の数値等）を、最新の制度・自治体運用と照らして確認する
- [ ] AdSenseの審査・広告コードの本番反映（`build.py` の `render_layout` 内、
      コメントアウトされているAdSenseスクリプトを有効化する）
- [ ] すべての確認が完了したら `NOINDEX = False` に変更し、再度 `python build.py` を
      実行してから最終デプロイする

## データの取り扱いについて

利用者名・用具情報・現場メモ等の入力データは、**サーバーには一切送信されず、
訪問者のブラウザ（localStorage）にのみ保存されます。** 詳細は `dist/privacy.html`
（`build.py` 内 `build_privacy()` 関数が生成）を参照してください。
