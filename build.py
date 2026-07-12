# -*- coding: utf-8 -*-
"""
========================================================================
build.py
補装具・日常生活用具「更新時期管理＆選び方ナビ」ビルドスクリプト
========================================================================
このスクリプトを実行すると、build_src/ 配下のデータ・記事コンテンツと、
static/ 配下のCSS・JSを組み合わせて、公開用の静的サイト（dist/ フォルダ）を
生成します。

  python build.py

生成された dist/ フォルダを、Cloudflare Workers（Assets）にデプロイします
（.github/workflows/deploy.yml 参照）。

【重要】公開（noindex解除）前は、必ず NOINDEX = True のままにしてください。
すべてのページに <meta name="robots" content="noindex,nofollow"> が
挿入され、robots.txt でもクロールを禁止する設定になります。
========================================================================
"""

import json
import os
import shutil
from datetime import date

from content_data import (  # noqa: E402
    EQUIPMENT_LIST,
    get_equipment_by_id,
    EQUIPMENT_ARTICLES,
    SYSTEM_ARTICLES,
)


# ========================================================================
# セクション1：サイト全体設定
# ========================================================================

# 【公開前チェックリスト】完成するまでは必ず True のままにしてください
NOINDEX = False

SITE_NAME = "補装具・日常生活用具ナビ"
ADSENSE_CLIENT_ID = "ca-pub-2908004621823900"
SITE_CATCH = "更新時期の管理と、用具選びの安心をひとつに"
# ドメインは設計書8章の案。実際のカスタムドメイン確定後に書き換えてください。
SITE_URL = "https://fukusiyougu.pray-power-is-god-and-cocoro.com"
SITE_DESCRIPTION = (
    "補装具・日常生活用具の耐用年数と再支給の時期を無料で管理できるツールと、"
    "相談支援の実務経験に基づく用具の選び方・制度解説記事をまとめたサイトです。"
)
OPERATOR_NAME = "ちゃろ"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "dist")

TODAY_STR = date.today().isoformat()


# ========================================================================
# セクション2：共通レイアウト（ヘッダー・フッター・meta情報）
# ========================================================================

def render_layout(title, meta_description, content_html, canonical_path="/",
                   script_extra=""):
    """
    サイト共通のHTMLレイアウトを組み立てる。
    title            : ページタイトル（<title>タグ用）
    meta_description : メタディスクリプション
    content_html     : <main>内に挿入する本文HTML
    canonical_path   : カノニカルURLのパス（例："/articles/wheelchair.html"）
    script_extra     : ページ固有で追加読み込みしたいscriptタグ（任意）
    """
    robots_tag = (
        '<meta name="robots" content="noindex,nofollow">'
        if NOINDEX else
        '<meta name="robots" content="index,follow">'
    )
    canonical_url = SITE_URL.rstrip("/") + canonical_path

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{meta_description}">
{robots_tag}
<link rel="canonical" href="{canonical_url}">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;700&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css?v=1">
<!-- ============================================================
     Google AdSense（スクリプトはページに1回だけ・head内で読み込む）     
     ============================================================ -->
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2908004621823900" crossorigin="anonymous"></script>     
</head>
<body>
<a class="skip-link" href="#main-content">本文へスキップ</a>

<!-- ============ ヘッダー ============ -->
<header class="site-header">
  <div class="header-inner">
    <a class="site-logo" href="/">
      <span class="logo-mark">＋</span>
      <span class="logo-text">{SITE_NAME}</span>
    </a>
    <nav class="site-nav" aria-label="メインナビゲーション">
      <a href="/">更新時期管理ツール</a>
      <a href="/articles/">用具・制度の解説記事</a>
      <a href="/about.html">運営者について</a>
    </nav>
  </div>
</header>

<main id="main-content">
{content_html}
</main>

<!-- ============ フッター ============ -->
<footer class="site-footer">
  <div class="footer-inner">
    <p class="footer-disclaimer">
      本サイトの情報は一般的な目安です。正式な判定・支給の可否は、
      必ずお住まいの自治体窓口・身体障害者更生相談所にご確認ください。
    </p>
    <nav class="footer-nav" aria-label="フッターナビゲーション">
      <a href="/about.html">運営者について</a>
      <a href="/privacy.html">データの取り扱い・免責事項</a>
      <a href="/articles/">記事一覧</a>
    </nav>
    <p class="footer-copyright">&copy; {date.today().year} {SITE_NAME}</p>
  </div>
</footer>

<button type="button" id="back-to-top" class="back-to-top" aria-label="ページの一番上に戻る">↑</button>
<script src="/script.js?v=1"></script>
{script_extra}
</body>
</html>
"""


# ========================================================================
# セクション3：トップページ（更新時期管理ツール）の生成
# ========================================================================

def build_equipment_options_html():
    """用具選択セレクトボックスの<option>群を生成する"""
    options = []
    for item in EQUIPMENT_LIST:
        options.append(
            f'<option value="{item["id"]}" '
            f'data-duration-years="{item["duration_years"]}" '
            f'data-category="{item["category"]}">'
            f'{item["name"]}（耐用年数目安：{item["duration_note"]}）'
            f'</option>'
        )
    return "\n".join(options)


def build_index():
    equipment_options = build_equipment_options_html()

    # 用具マスタデータ（耐用年数テーブル）をJSONとしてJS側に渡す。
    # content_data.py を唯一の情報源（single source of truth）とし、
    # JS側では複製せずこのJSONを参照することでデータの二重管理を避ける。
    equipment_data_json = json.dumps(EQUIPMENT_LIST, ensure_ascii=False)
    equipment_data_script = (
        f'<script>window.EQUIPMENT_DATA = {equipment_data_json};</script>'
    )

    content_html = f"""
{equipment_data_script}
<!-- ============ ヒーローセクション ============ -->
<section class="hero">
  <!-- 装飾用の背景（太陽・白い雲・虹・ふわふわ浮かぶ福祉用具アイコン） -->
  <div class="hero-bg" aria-hidden="true">
    <svg viewBox="0 0 1600 640" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="skyGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#8FCBEA"/>
          <stop offset="55%" stop-color="#CBE9DE"/>
          <stop offset="100%" stop-color="#F1F8F1"/>
        </linearGradient>
        <radialGradient id="sunGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#FFEBB0" stop-opacity="0.95"/>
          <stop offset="100%" stop-color="#FFEBB0" stop-opacity="0"/>
        </radialGradient>
      </defs>

      <rect x="0" y="0" width="1600" height="640" fill="url(#skyGradient)"/>

      <!-- 太陽 -->
      <circle cx="1370" cy="120" r="150" fill="url(#sunGlow)"/>
      <circle cx="1370" cy="120" r="60" fill="#FFD873"/>

      <!-- 虹（アーチ状） -->
      <g fill="none" stroke-width="14" stroke-linecap="round" opacity="0.85">
        <path d="M 160 560 A 520 520 0 0 1 1180 560" stroke="#E8836F"/>
        <path d="M 192 560 A 490 490 0 0 1 1148 560" stroke="#F0A85A"/>
        <path d="M 224 560 A 460 460 0 0 1 1116 560" stroke="#F3CF62"/>
        <path d="M 256 560 A 430 430 0 0 1 1084 560" stroke="#8FBE7A"/>
        <path d="M 288 560 A 400 400 0 0 1 1052 560" stroke="#6FAFCB"/>
        <path d="M 320 560 A 370 370 0 0 1 1020 560" stroke="#8E92C9"/>
      </g>

      <!-- 白い雲（3グループ） -->
      <g fill="#FFFFFF" opacity="0.92">
        <ellipse cx="260" cy="150" rx="90" ry="34"/>
        <ellipse cx="330" cy="130" rx="70" ry="30"/>
        <ellipse cx="200" cy="140" rx="60" ry="26"/>
      </g>
      <g fill="#FFFFFF" opacity="0.85">
        <ellipse cx="1050" cy="90" rx="80" ry="28"/>
        <ellipse cx="1110" cy="105" rx="60" ry="24"/>
      </g>
      <g fill="#FFFFFF" opacity="0.8">
        <ellipse cx="780" cy="60" rx="70" ry="24"/>
        <ellipse cx="830" cy="75" rx="50" ry="20"/>
      </g>

      <!-- ふわふわ浮かぶ福祉用具アイコン（内側のgのみCSSアニメーションで上下に揺れる） -->
      <g transform="translate(210,330)">
        <g class="float-icon float-icon-1">
          <!-- 車椅子（簡易アイコン） -->
          <g stroke="#1F4B49" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.55">
            <circle cx="0" cy="30" r="26"/>
            <circle cx="60" cy="38" r="14"/>
            <path d="M0 4 L0 -26 L34 -26"/>
            <path d="M0 4 L46 4 L60 24"/>
            <path d="M34 -26 L46 4"/>
          </g>
        </g>
      </g>

      <g transform="translate(560,470)">
        <g class="float-icon float-icon-2">
          <!-- 歩行補助つえ -->
          <g stroke="#1F4B49" stroke-width="6" fill="none" stroke-linecap="round" opacity="0.5">
            <path d="M0 -60 L0 60"/>
            <path d="M0 -60 C 16 -70, 26 -60, 22 -46"/>
          </g>
        </g>
      </g>

      <g transform="translate(900,380)">
        <g class="float-icon float-icon-3">
          <!-- 歩行器（簡易フレーム） -->
          <g stroke="#1F4B49" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.5">
            <path d="M-30 40 L-30 -20 L30 -20 L30 40"/>
            <path d="M-30 40 L-40 55 M-30 40 L-20 55"/>
            <path d="M30 40 L40 55 M30 40 L20 55"/>
          </g>
        </g>
      </g>

      <g transform="translate(1230,300)">
        <g class="float-icon float-icon-4">
          <!-- 特殊寝台（簡易ベッド） -->
          <g stroke="#1F4B49" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.5">
            <path d="M-40 20 L40 20 L40 -10 L-20 -10 L-20 5 L-40 5 Z"/>
            <path d="M-40 20 L-40 34 M40 20 L40 34"/>
          </g>
        </g>
      </g>
    </svg>
  </div>

  <div class="hero-inner">
    <p class="hero-eyebrow">相談支援専門員・福祉用具担当者のための<br>無料ツール</p>
    <h1 class="hero-title">補装具・日常生活用具の<br>更新時期、まとめて見える化。</h1>
    <p class="hero-lead">{SITE_DESCRIPTION}</p>
    <p class="hero-note">登録不要・完全無料。入力内容はお使いの端末だけに保存されます。</p>
  </div>
</section>

<!-- ============ ダッシュボード（件数集計） ============ -->
<section class="dashboard" aria-label="登録状況ダッシュボード">
  <div class="dashboard-inner">
    <div class="dashboard-card dashboard-card--danger">
      <span class="dashboard-number" id="dash-30">0</span>
      <span class="dashboard-label">30日以内に準備が必要</span>
    </div>
    <div class="dashboard-card dashboard-card--warning">
      <span class="dashboard-number" id="dash-90">0</span>
      <span class="dashboard-label">90日以内に準備が必要</span>
    </div>
    <div class="dashboard-card dashboard-card--info">
      <span class="dashboard-number" id="dash-year">0</span>
      <span class="dashboard-label">今年度中に更新予定</span>
    </div>
    <div class="dashboard-card">
      <span class="dashboard-number" id="dash-total">0</span>
      <span class="dashboard-label">登録件数</span>
    </div>
  </div>
</section>

<!-- ============ 入力フォーム ============ -->
<section class="tool-section" aria-label="用具の登録フォーム">
  <div class="tool-inner">
    <h2 class="section-title">利用者・用具の登録</h2>
    <form id="equipment-form" class="equipment-form" autocomplete="off">
      <div class="form-row">
        <label for="input-user-name">利用者名<br>（任意・この端末にのみ保存されます）</label>
        <input type="text" id="input-user-name" name="userName" placeholder="例：A様">
      </div>

      <div class="form-row">
        <label for="input-equipment-type">用具の種類</label>
        <select id="input-equipment-type" name="equipmentType" required>
          <option value="">選択してください</option>
          {equipment_options}
        </select>
      </div>

      <div class="form-row">
        <label for="input-decision-date">交付決定日（前回支給を受けた日）</label>
        <input type="date" id="input-decision-date" name="decisionDate" required>
      </div>

      <div class="form-row form-row--checkbox">
        <label>
          <input type="checkbox" id="input-exception-flag" name="exceptionFlag">
          破損・身体状況の変化等、耐用年数内での再支給を検討している事情がある
        </label>
      </div>

      <div class="form-row">
        <label for="input-memo">現場メモ<br>（任意・自治体独自ルール等の記録に）</label>
        <textarea id="input-memo" name="memo" rows="2"
          placeholder="例：〇〇市は申請に追加書類が必要"></textarea>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary">登録する</button>
      </div>
    </form>

    <p class="tool-caption">
      ※ 判定結果はすべて目安です。正式な判定は自治体窓口・身体障害者更生相談所にご確認ください。
      耐用年数内であっても、破損や身体状況の変化により再支給が認められる場合があります。
    </p>
  </div>
</section>

<!-- ============ 一覧表示・操作エリア ============ -->
<section class="list-section" aria-label="登録済み一覧">
  <div class="list-inner">
    <div class="list-header">
      <h2 class="section-title">登録済み一覧</h2>
      <div class="list-actions">
        <button type="button" id="btn-export-csv" class="btn btn-secondary">CSVエクスポート</button>
        <button type="button" id="btn-print" class="btn btn-secondary">印刷／チェックリストPDF</button>
      </div>
    </div>

    <div class="table-wrap">
      <table id="equipment-table" class="equipment-table">
        <thead>
          <tr>
            <th>利用者名</th>
            <th>用具</th>
            <th>交付決定日</th>
            <th>次回申請可能時期</th>
            <th>意見書準備目安</th>
            <th>残り日数</th>
            <th>現場メモ</th>
            <th class="print-hide">操作</th>
          </tr>
        </thead>
        <tbody id="equipment-table-body">
          <!-- JavaScriptにより動的に描画されます -->
        </tbody>
      </table>
      <p id="empty-state" class="empty-state">まだ登録がありません。上のフォームから登録してください。</p>
    </div>
  </div>
</section>

<!-- ============ 印刷用チェックリストのテンプレート（画面には非表示） ============ -->
<section id="print-checklist" class="print-checklist" aria-hidden="true">
  <h2>更新準備チェックリスト</h2>
  <div id="print-checklist-body"></div>
</section>

<!-- ============ 内部リンク：記事への回遊 ============ -->
<section class="related-section">
  <div class="related-inner">
    <h2 class="section-title">用具の選び方・制度の解説記事</h2>
    <p>耐用年数の考え方や、用具ごとの選び方は、以下の記事でも解説しています。</p>
    <a class="btn btn-outline" href="/articles/">記事一覧を見る</a>
  </div>
</section>

<section class="ad-section">
  <div class="ad-section-inner">
   
<ins class="adsbygoogle"
     style="display:block; text-align:center;"
     data-ad-layout="in-article"
     data-ad-format="fluid"
     data-ad-client="ca-pub-2908004621823900"
     data-ad-slot="5820083954"></ins>
<script>
     (adsbygoogle = window.adsbygoogle || []).push({{}});
</script>

  </div>
</section>


"""
    return render_layout(
        title=f"{SITE_NAME}｜{SITE_CATCH}",
        meta_description=SITE_DESCRIPTION,
        content_html=content_html,
        canonical_path="/",
    )


# ========================================================================
# セクション4：用具データベース型記事の生成
# ========================================================================

def build_equipment_article_html(article):
    """EQUIPMENT_ARTICLES の1件から記事本文HTMLを生成する"""
    equipment = get_equipment_by_id(article["id"])

    select_points_html = "\n".join(
        f"<li>{point}</li>" for point in article["select_points"]
    )

    faq_html = ""
    for qa in article["faq"]:
        faq_html += f"""
      <div class="faq-item">
        <p class="faq-q">Q. {qa["q"]}</p>
        <p class="faq-a">A. {qa["a"]}</p>
      </div>"""

    category_label = "補装具" if equipment["category"] == "hosogu" else "日常生活用具"

    body = f"""
<article class="article">
  <div class="article-inner">
    <p class="article-eyebrow">{category_label}の解説記事</p>
    <h1 class="article-title">{article["title"]}</h1>
    <p class="article-lead">{article["lead"]}</p>

    <h2>対象となる方</h2>
    <p>{article["target"]}</p>

    <h2>特徴</h2>
    <p>{article["feature"]}</p>

    <h2>メリット</h2>
    <p>{article["merit"]}</p>

    <h2>デメリット・注意点</h2>
    <p>{article["demerit"]}</p>

    <h2>耐用年数の目安</h2>
    <p>{article["duration_text"]}</p>
    <p class="disclaimer-inline">
      ※ 耐用年数は目安であり、身体状況や自治体の判断により取り扱いが異なる場合があります。
      正式な判定は自治体窓口・身体障害者更生相談所にご確認ください。
    </p>

    <h2>選び方のポイント</h2>
    <ul>
      {select_points_html}
    </ul>

    <div class="genba-memo">
      <p>{article["genba_memo"]}</p>
    </div>

    <h2>よくある質問</h2>
    <div class="faq-list">
      {faq_html}
    </div>

    <div class="article-cta">
      <p>この用具の更新時期は、無料の管理ツールでまとめて確認できます。</p>
      <a class="btn btn-primary" href="/#equipment-form">更新時期管理ツールを使う</a>
    </div>

    <div class="article-related">
      <a href="/articles/">記事一覧に戻る</a>
    </div>
  </div>
</article>
"""
    return render_layout(
        title=f"{article['title']}｜{SITE_NAME}",
        meta_description=article["meta_description"],
        content_html=body,
        canonical_path=f"/articles/{article['id']}.html",
    )


# ========================================================================
# セクション5：制度解説記事（システム記事）の生成
# ========================================================================

def build_system_article_html(article):
    body = f"""
<article class="article">
  <div class="article-inner">
    <p class="article-eyebrow">制度の解説記事</p>
    <h1 class="article-title">{article["title"]}</h1>
    {article["body"]}
    <div class="article-related">
      <a href="/articles/">記事一覧に戻る</a>
    </div>
  </div>
</article>
"""
    return render_layout(
        title=f"{article['title']}｜{SITE_NAME}",
        meta_description=article["meta_description"],
        content_html=body,
        canonical_path=f"/articles/{article['id']}.html",
    )


# ========================================================================
# セクション6：記事一覧ページ（ハブページ）の生成
# ========================================================================

def build_articles_index():
    equipment_items_html = ""
    for a in EQUIPMENT_ARTICLES:
        equipment_items_html += f"""
      <li class="article-list-item">
        <a href="/articles/{a['id']}.html">{a['title']}</a>
        <p>{a['meta_description']}</p>
      </li>"""

    system_items_html = ""
    for a in SYSTEM_ARTICLES:
        system_items_html += f"""
      <li class="article-list-item">
        <a href="/articles/{a['id']}.html">{a['title']}</a>
        <p>{a['meta_description']}</p>
      </li>"""

    content_html = f"""
<section class="article-index">
  <div class="article-index-inner">
    <h1 class="section-title">用具・制度の解説記事一覧</h1>

    <h2>制度の基本を知る</h2>
    <ul class="article-list">
      {system_items_html}
    </ul>

    <h2>用具ごとの選び方・耐用年数</h2>
    <ul class="article-list">
      {equipment_items_html}
    </ul>
  </div>
</section>
"""
    return render_layout(
        title=f"用具・制度の解説記事一覧｜{SITE_NAME}",
        meta_description="補装具・日常生活用具の制度解説と、用具ごとの選び方・耐用年数をまとめた記事一覧です。",
        content_html=content_html,
        canonical_path="/articles/",
    )


# ========================================================================
# セクション7：運営者情報ページ（E-E-A-T）
# ========================================================================

def build_about():
    content_html = f"""
<section class="static-page">
  <div class="static-page-inner">
    <h1 class="section-title">運営者について</h1>
    <p>本サイトは、障害福祉サービスの相談支援専門員の方々が、お忙しい日々の相談支援業務の中でもっと快適に業務を行っていただければ、という思いから制作・運営しています。</p>

    <h2>本サイトを作った理由</h2>
    <p>補装具・日常生活用具の耐用年数や再支給の時期は、担当する利用者が増えるほど
    手帳や表計算ソフトでの個別管理が煩雑になります。この管理業務を、無料で・
    登録不要で・誰でも使えるツールにすることで、相談支援専門員をはじめとする
    福祉の現場で働く方々の実務負担を少しでも軽くしたいと考えています。</p>

    <h2>情報の正確性について</h2>
    <p>本サイトに掲載する制度情報は、厚生労働省の告示・通知や、自治体の公表資料を
    参考にしていますが、内容の正確性・最新性を完全に保証するものではありません。
    制度は改定されることがあるため、実際の申請・判定にあたっては、必ずお住まいの
    自治体窓口・身体障害者更生相談所にご確認ください。</p>

  </div>
</section>
"""
    return render_layout(
        title=f"運営者について｜{SITE_NAME}",
        meta_description=f"{SITE_NAME}の運営者情報・制作の背景について紹介しています。",
        content_html=content_html,
        canonical_path="/about.html",
    )


# ========================================================================
# セクション8：データの取り扱い・免責事項ページ
# ========================================================================

def build_privacy():
    content_html = f"""
<section class="static-page">
  <div class="static-page-inner">
    <h1 class="section-title">データの取り扱い・免責事項</h1>

    <h2>入力データの保存について</h2>
    <p>本サイトの更新時期管理ツールに入力いただいた利用者名・用具情報・メモ等の
    データは、<strong>サーバーには一切送信・保存されません。お使いのブラウザ
    （端末）にのみ保存されます。</strong></p>
    <p class="highlight-box">
      あなただけのブラウザに保存されます。安心してください。ただし、違う端末や
      別のブラウザでアクセスすると、データが表示されない場合があります。
      端末を変更する際は、CSVエクスポート機能をご利用ください。
    </p>

    <h2>免責事項</h2>
    <ul>
      <li>本サイトに掲載する耐用年数・制度情報は、一般的な目安であり、
        すべてのケースに当てはまることを保証するものではありません。</li>
      <li>正式な判定・支給の可否は、必ずお住まいの自治体窓口・
        身体障害者更生相談所にご確認ください。</li>
      <li>日常生活用具は市町村事業のため、対象品目・基準・耐用年数が
        自治体により異なる場合があります。</li>
      <li>耐用年数内であっても、身体状況の変化や破損等により、
        再支給が認められる場合があります。</li>
      <li>制度改定により、本サイトの情報が最新ではない場合があります。</li>
    </ul>

    <h2>広告について</h2>
    <p>本サイトでは、Google AdSenseによる広告を掲載しています。</p>
  </div>
</section>
"""
    return render_layout(
        title=f"データの取り扱い・免責事項｜{SITE_NAME}",
        meta_description="本サイトのデータ保存方針（ブラウザ内保存のみ）と免責事項について説明しています。",
        content_html=content_html,
        canonical_path="/privacy.html",
    )


# ========================================================================
# セクション9：sitemap.xml / robots.txt の生成
# ========================================================================

def build_sitemap(all_paths):
    urls = ""
    for path in all_paths:
        urls += f"""  <url>
    <loc>{SITE_URL}{path}</loc>
    <lastmod>{TODAY_STR}</lastmod>
  </url>
"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}</urlset>
"""


def build_robots():
    if NOINDEX:
        return "User-agent: *\nDisallow: /\n"
    return f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"


# ========================================================================
# セクション10：favicon（実ファイルとして用意し、data URIの事故を避ける）
# ========================================================================

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#1F4B49"/>
  <path d="M32 14 L32 50 M14 32 L50 32" stroke="#F4E9D8" stroke-width="8" stroke-linecap="round"/>
</svg>
"""


# ========================================================================
# セクション11：ビルド実行本体
# ========================================================================

def clean_output_dir():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)
    os.makedirs(os.path.join(OUTPUT_DIR, "articles"))


def write_file(relative_path, content):
    full_path = os.path.join(OUTPUT_DIR, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)


def copy_static_assets():
    shutil.copy(os.path.join(BASE_DIR, "style.css"), os.path.join(OUTPUT_DIR, "style.css"))
    shutil.copy(os.path.join(BASE_DIR, "script.js"), os.path.join(OUTPUT_DIR, "script.js"))
    write_file("favicon.svg", FAVICON_SVG)


def main():
    print("=" * 60)
    print("ビルド開始：補装具・日常生活用具ナビ")
    print(f"NOINDEX モード: {NOINDEX}")
    print("=" * 60)

    clean_output_dir()

    all_paths = []

    # --- トップページ ---
    write_file("index.html", build_index())
    all_paths.append("/")
    print("生成: index.html")

    # --- 用具データベース型記事 ---
    for article in EQUIPMENT_ARTICLES:
        html = build_equipment_article_html(article)
        rel_path = f"articles/{article['id']}.html"
        write_file(rel_path, html)
        all_paths.append(f"/{rel_path}")
        print(f"生成: {rel_path}")

    # --- 制度解説記事 ---
    for article in SYSTEM_ARTICLES:
        html = build_system_article_html(article)
        rel_path = f"articles/{article['id']}.html"
        write_file(rel_path, html)
        all_paths.append(f"/{rel_path}")
        print(f"生成: {rel_path}")

    # --- 記事一覧ページ ---
    write_file("articles/index.html", build_articles_index())
    all_paths.append("/articles/")
    print("生成: articles/index.html")

    # --- 運営者情報・免責事項 ---
    write_file("about.html", build_about())
    all_paths.append("/about.html")
    print("生成: about.html")

    write_file("privacy.html", build_privacy())
    all_paths.append("/privacy.html")
    print("生成: privacy.html")

    # --- 静的アセット（CSS/JS/favicon） ---
    copy_static_assets()
    print("コピー: style.css, script.js, favicon.svg")

    # --- sitemap.xml / robots.txt ---
    write_file("sitemap.xml", build_sitemap(all_paths))
    write_file("robots.txt", build_robots())
    print("生成: sitemap.xml, robots.txt")

    print("=" * 60)
    print(f"ビルド完了。出力先: {OUTPUT_DIR}")
    if NOINDEX:
        print("★ 現在 NOINDEX = True です。公開準備が整うまではこのままにしてください。")
    print("=" * 60)


if __name__ == "__main__":
    main()
