/* ========================================================================
 * script.js
 * 補装具・日常生活用具「更新時期管理＆選び方ナビ」トップページのロジック
 * ========================================================================
 * このファイルは index.html（トップページ）でのみ主要な機能が動作する。
 * 記事ページ等では #equipment-form 等の要素が存在しないため、
 * 各処理の冒頭でnullチェックを行い、安全に何もしないようにしている。
 * ======================================================================== */

(function () {
  "use strict";

  /* ----------------------------------------------------------------------
   * セクション1：定数・状態管理
   * -------------------------------------------------------------------- */

  var STORAGE_KEY = "hosogu-navi:items:v1";

  // build.py（index.html生成時）が window.EQUIPMENT_DATA にJSONを埋め込む。
  // 記事ページ等、埋め込みがないページでは空配列にフォールバックする。
  var EQUIPMENT_DATA = window.EQUIPMENT_DATA || [];

  // 実務スケジュール逆算の目安（設計書 5-2-1）。
  // 「更新予定日（次回申請可能時期）」からの逆算の月数。
  var SCHEDULE_OFFSETS_MONTHS = [
    { key: "applyStart", label: "申請開始目安", months: 3 },
    { key: "doctorAppointment", label: "判定医（主治医等）への予約目安", months: 2.5 },
    { key: "opinionLetter", label: "意見書依頼目安", months: 2 },
    { key: "vendorConsult", label: "業者への見積相談目安", months: 1.5 },
    { key: "submitApplication", label: "申請書提出目安", months: 1 },
  ];

  /* ----------------------------------------------------------------------
   * セクション2：日付計算ユーティリティ
   * -------------------------------------------------------------------- */

  /**
   * "YYYY-MM-DD" 形式の文字列をローカルタイムのDateオブジェクトに変換する。
   * new Date("YYYY-MM-DD") はUTCとして解釈されタイムゾーンによりズレることが
   * あるため、年月日を分解して明示的にローカル日付を組み立てる。
   */
  function parseDateInput(dateStr) {
    if (!dateStr) return null;
    var parts = dateStr.split("-");
    if (parts.length !== 3) return null;
    var y = parseInt(parts[0], 10);
    var m = parseInt(parts[1], 10) - 1;
    var d = parseInt(parts[2], 10);
    var dt = new Date(y, m, d);
    if (isNaN(dt.getTime())) return null;
    return dt;
  }

  function formatDate(dt) {
    if (!dt) return "";
    var y = dt.getFullYear();
    var m = String(dt.getMonth() + 1).padStart(2, "0");
    var d = String(dt.getDate()).padStart(2, "0");
    return y + "-" + m + "-" + d;
  }

  /**
   * 日付に「年」を加算する。うるう年の2/29に加算した結果、
   * 加算後の年がうるう年でない場合はJSのDateが自動的に3/1へ繰り上げる
   * （＝月末クランプと同様の考え方で安全側に倒れる）。
   */
  function addYears(dt, years) {
    var result = new Date(dt.getTime());
    result.setFullYear(result.getFullYear() + years);
    return result;
  }

  /**
   * 日付に「月」を加算する（小数月にも対応：0.5ヶ月＝約15日として扱う）。
   * setMonthは月末日を超えるとJSが自動的に翌月へ繰り上げるため、
   * 「31日の3ヶ月前が2月31日」のような不正日付は自動的に補正される。
   */
  function subtractMonths(dt, months) {
    var wholeMonths = Math.floor(months);
    var fraction = months - wholeMonths;
    var result = new Date(dt.getTime());
    result.setMonth(result.getMonth() - wholeMonths);
    if (fraction > 0) {
      // 0.5ヶ月分は概算で15日として日数から差し引く
      result.setDate(result.getDate() - Math.round(fraction * 30));
    }
    return result;
  }

  function daysBetween(fromDt, toDt) {
    var msPerDay = 1000 * 60 * 60 * 24;
    // 時刻成分の誤差を避けるため、日付だけの午前0時同士で比較する
    var a = new Date(fromDt.getFullYear(), fromDt.getMonth(), fromDt.getDate());
    var b = new Date(toDt.getFullYear(), toDt.getMonth(), toDt.getDate());
    return Math.round((b.getTime() - a.getTime()) / msPerDay);
  }

  /* ----------------------------------------------------------------------
   * セクション3：localStorage 読み書き
   * -------------------------------------------------------------------- */

  function loadItems() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      var parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed;
    } catch (err) {
      console.error("データの読み込みに失敗しました:", err);
      return [];
    }
  }

  function saveItems(items) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
      return true;
    } catch (err) {
      console.error("データの保存に失敗しました:", err);
      window.alert(
        "データの保存に失敗しました。ブラウザの空き容量やプライベートブラウジング設定をご確認ください。"
      );
      return false;
    }
  }

  function generateId() {
    return "item-" + Date.now() + "-" + Math.floor(Math.random() * 100000);
  }

  /* ----------------------------------------------------------------------
   * セクション4：判定ロジック（耐用年数・スケジュール逆算）
   * -------------------------------------------------------------------- */

  function findEquipmentMeta(equipmentId) {
    for (var i = 0; i < EQUIPMENT_DATA.length; i++) {
      if (EQUIPMENT_DATA[i].id === equipmentId) return EQUIPMENT_DATA[i];
    }
    return null;
  }

  /**
   * 1件分の登録データから、判定結果（次回申請可能時期・意見書準備目安・
   * 残り日数・実務スケジュール一式）を計算する。
   */
  function computeResult(item) {
    var decisionDate = parseDateInput(item.decisionDate);
    if (!decisionDate) return null;

    var durationYears = item.durationYears || 0;
    var nextApplicationDate = addYears(decisionDate, durationYears);

    var schedule = SCHEDULE_OFFSETS_MONTHS.map(function (step) {
      return {
        key: step.key,
        label: step.label,
        date: subtractMonths(nextApplicationDate, step.months),
      };
    });

    var opinionLetterStep = schedule.filter(function (s) {
      return s.key === "opinionLetter";
    })[0];

    var today = new Date();
    var remainingDays = daysBetween(today, nextApplicationDate);

    var urgency = "safe"; // safe / warning / danger
    if (remainingDays <= 30) {
      urgency = "danger";
    } else if (remainingDays <= 90) {
      urgency = "warning";
    }

    return {
      nextApplicationDate: nextApplicationDate,
      opinionLetterDate: opinionLetterStep ? opinionLetterStep.date : null,
      schedule: schedule,
      remainingDays: remainingDays,
      urgency: urgency,
    };
  }

  /* ----------------------------------------------------------------------
   * セクション5：一覧テーブルの描画
   * -------------------------------------------------------------------- */

  function renderTable(items) {
    var tbody = document.getElementById("equipment-table-body");
    var emptyState = document.getElementById("empty-state");
    if (!tbody) return; // トップページ以外では何もしない

    tbody.innerHTML = "";

    if (items.length === 0) {
      if (emptyState) emptyState.style.display = "block";
      updateDashboard(items);
      return;
    }
    if (emptyState) emptyState.style.display = "none";

    // 残り日数が短い順（緊急度が高い順）に並び替えて表示する
    var withResults = items
      .map(function (item) {
        return { item: item, result: computeResult(item) };
      })
      .filter(function (row) {
        return row.result !== null;
      });

    withResults.sort(function (a, b) {
      return a.result.remainingDays - b.result.remainingDays;
    });

    withResults.forEach(function (row) {
      var item = row.item;
      var result = row.result;
      var tr = document.createElement("tr");
      tr.className = "row-urgency-" + result.urgency;

      var remainingLabel =
        result.remainingDays >= 0
          ? "あと" + result.remainingDays + "日"
          : "期限超過（" + Math.abs(result.remainingDays) + "日経過）";

      tr.innerHTML =
        "<td>" + escapeHtml(item.userName || "（未入力）") + "</td>" +
        "<td>" + escapeHtml(item.equipmentName || "") + "</td>" +
        "<td>" + escapeHtml(item.decisionDate || "") + "</td>" +
        "<td>" + formatDate(result.nextApplicationDate) + "</td>" +
        "<td>" + formatDate(result.opinionLetterDate) + "</td>" +
        "<td><span class='badge badge-" + result.urgency + "'>" + remainingLabel + "</span></td>" +
        "<td class='memo-cell'>" +
          "<input type='text' class='memo-input' data-item-id='" + item.id + "' value=\"" +
          escapeHtml(item.memo || "") + "\" placeholder='自治体ルール等のメモ'>" +
        "</td>" +
        "<td class='print-hide'>" +
          "<button type='button' class='btn-delete' data-item-id='" + item.id + "'>削除</button>" +
        "</td>";

      tbody.appendChild(tr);
    });

    updateDashboard(items);
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  /* ----------------------------------------------------------------------
   * セクション6：ダッシュボード（件数集計）
   * -------------------------------------------------------------------- */

  function updateDashboard(items) {
    var dash30 = document.getElementById("dash-30");
    var dash90 = document.getElementById("dash-90");
    var dashYear = document.getElementById("dash-year");
    var dashTotal = document.getElementById("dash-total");
    if (!dash30 || !dash90 || !dashYear || !dashTotal) return;

    var count30 = 0;
    var count90 = 0;
    var countYear = 0;
    var thisYear = new Date().getFullYear();

    items.forEach(function (item) {
      var result = computeResult(item);
      if (!result) return;
      if (result.remainingDays <= 30) count30++;
      if (result.remainingDays <= 90) count90++;
      // 「今年度中」は簡略化のため「今年12月31日まで」として集計する
      if (result.nextApplicationDate.getFullYear() === thisYear) countYear++;
    });

    dash30.textContent = String(count30);
    dash90.textContent = String(count90);
    dashYear.textContent = String(countYear);
    dashTotal.textContent = String(items.length);
  }

  /* ----------------------------------------------------------------------
   * セクション7：フォーム送信・削除・メモ編集の各種イベント
   * -------------------------------------------------------------------- */

  function initForm() {
    var form = document.getElementById("equipment-form");
    if (!form) return; // トップページ以外では何もしない

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      var userNameEl = document.getElementById("input-user-name");
      var equipmentSelectEl = document.getElementById("input-equipment-type");
      var decisionDateEl = document.getElementById("input-decision-date");
      var exceptionFlagEl = document.getElementById("input-exception-flag");
      var memoEl = document.getElementById("input-memo");

      var equipmentId = equipmentSelectEl.value;
      var decisionDate = decisionDateEl.value;

      if (!equipmentId || !decisionDate) {
        window.alert("用具の種類と交付決定日は必須です。");
        return;
      }

      var meta = findEquipmentMeta(equipmentId);
      if (!meta) {
        window.alert("用具データの取得に失敗しました。ページを再読み込みしてください。");
        return;
      }

      var items = loadItems();
      items.push({
        id: generateId(),
        userName: userNameEl.value.trim(),
        equipmentId: equipmentId,
        equipmentName: meta.name,
        category: meta.category,
        durationYears: meta.duration_years,
        decisionDate: decisionDate,
        exceptionFlag: !!exceptionFlagEl.checked,
        memo: memoEl.value.trim(),
        createdAt: new Date().toISOString(),
      });

      if (saveItems(items)) {
        renderTable(items);
        form.reset();
        userNameEl.focus();
      }
    });

    // 一覧テーブル内の「削除」ボタン・メモ入力欄（イベント委譲）
    var tbody = document.getElementById("equipment-table-body");
    if (tbody) {
      tbody.addEventListener("click", function (event) {
        var target = event.target;
        if (target.classList.contains("btn-delete")) {
          var itemId = target.getAttribute("data-item-id");
          if (!window.confirm("この登録を削除しますか？")) return;
          var items = loadItems().filter(function (it) {
            return it.id !== itemId;
          });
          saveItems(items);
          renderTable(items);
        }
      });

      tbody.addEventListener("change", function (event) {
        var target = event.target;
        if (target.classList.contains("memo-input")) {
          var itemId = target.getAttribute("data-item-id");
          var items = loadItems();
          var updated = items.map(function (it) {
            if (it.id === itemId) {
              it.memo = target.value;
            }
            return it;
          });
          saveItems(updated);
        }
      });
    }
  }

  /* ----------------------------------------------------------------------
   * セクション8：CSVエクスポート
   * -------------------------------------------------------------------- */

  function initCsvExport() {
    var button = document.getElementById("btn-export-csv");
    if (!button) return;

    button.addEventListener("click", function () {
      var items = loadItems();
      if (items.length === 0) {
        window.alert("エクスポートするデータがありません。");
        return;
      }

      var header = [
        "利用者名", "用具", "交付決定日", "次回申請可能時期",
        "意見書準備目安", "残り日数", "現場メモ",
      ];
      var rows = [header];

      items.forEach(function (item) {
        var result = computeResult(item);
        if (!result) return;
        rows.push([
          item.userName || "",
          item.equipmentName || "",
          item.decisionDate || "",
          formatDate(result.nextApplicationDate),
          formatDate(result.opinionLetterDate),
          String(result.remainingDays),
          item.memo || "",
        ]);
      });

      var csvContent = rows
        .map(function (row) {
          return row
            .map(function (cell) {
              var escaped = String(cell).replace(/"/g, '""');
              return '"' + escaped + '"';
            })
            .join(",");
        })
        .join("\r\n");

      // Excel等での文字化けを防ぐためBOMを付与する
      var blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = "hosogu-navi-" + formatDate(new Date()) + ".csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }

  /* ----------------------------------------------------------------------
   * セクション9：印刷用チェックリストの生成
   * -------------------------------------------------------------------- */

  function initPrint() {
    var button = document.getElementById("btn-print");
    var printArea = document.getElementById("print-checklist-body");
    if (!button || !printArea) return;

    button.addEventListener("click", function () {
      var items = loadItems();
      if (items.length === 0) {
        window.alert("印刷するデータがありません。");
        return;
      }

      var html = "";
      items
        .map(function (item) {
          return { item: item, result: computeResult(item) };
        })
        .filter(function (row) {
          return row.result !== null;
        })
        .sort(function (a, b) {
          return a.result.remainingDays - b.result.remainingDays;
        })
        .forEach(function (row) {
          var item = row.item;
          var result = row.result;
          var remainingLabel =
            result.remainingDays >= 0
              ? "あと" + result.remainingDays + "日"
              : "期限超過（" + Math.abs(result.remainingDays) + "日経過）";
          html += "<div class='print-item'>";
          html += "<h3>" + escapeHtml(item.userName || "（未入力）") + "　／　" +
            escapeHtml(item.equipmentName || "") + "</h3>";
          html += "<p>交付決定日：" + escapeHtml(item.decisionDate || "") + "</p>";
          html += "<p>次回申請可能時期：" + formatDate(result.nextApplicationDate) + "</p>";
          html += "<p>残り日数：" + remainingLabel + "</p>";
          html += "<ul class='print-check-steps'>";
          result.schedule.forEach(function (step) {
            html += "<li>□ " + escapeHtml(step.label) + "（目安：" + formatDate(step.date) + "）</li>";
          });
          html += "<li>□ 業者納品・完了確認</li>";
          html += "</ul>";
          if (item.memo) {
            html += "<p class='print-memo'>現場メモ：" + escapeHtml(item.memo) + "</p>";
          }
          html += "</div>";
        });

      printArea.innerHTML = html;
      window.print();
    });
  }

  /* ----------------------------------------------------------------------
   * セクション10：初期化
   * -------------------------------------------------------------------- */

  /* ----------------------------------------------------------------------
   * セクション11：ページトップに戻るボタン（全ページ共通）
   * -------------------------------------------------------------------- */
  function initBackToTop() {
    var button = document.getElementById("back-to-top");
    if (!button) return;

    function toggleVisibility() {
      if (window.scrollY > 400) {
        button.classList.add("is-visible");
      } else {
        button.classList.remove("is-visible");
      }
    }

    window.addEventListener("scroll", toggleVisibility, { passive: true });
    toggleVisibility();

    button.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  function init() {
    var items = loadItems();
    renderTable(items);
    initForm();
    initCsvExport();
    initPrint();
    initBackToTop();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
