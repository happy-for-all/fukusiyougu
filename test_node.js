// Node.js(jsdom)による動作検証スクリプト
// フォーム送信・削除・並び替え・耐用年数判定ロジック・境界値を検証する

const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

let html = fs.readFileSync(path.join(__dirname, "dist", "index.html"), "utf8");

// 外部フォント・CSSの読み込みタグを除去し、scriptタグはjsdomの自動フェッチに
// 任せず、後段でファイル内容を直接評価する方式に切り替える（オフライン環境での
// 誤検知を避けるため）。
html = html
  .replace(/<link[^>]*fonts\.googleapis[^>]*>/g, "")
  .replace(/<link[^>]*fonts\.gstatic[^>]*>/g, "")
  .replace(/<link[^>]*style\.css[^>]*>/g, "")
  .replace(/<script src="\/script\.js\?v=1"><\/script>/g, "");

async function run() {
  const dom = new JSDOM(html, {
    url: "http://localhost/",
    runScripts: "dangerously",
    pretendToBeVisual: true,
  });

  const { window } = dom;
  const document = window.document;

  // インラインで埋め込まれた window.EQUIPMENT_DATA の<script>はjsdomが
  // 通常のHTML解析時にそのまま実行するため、この時点で既に定義済みのはず。
  // その後、実際のツールロジック（script.js）の内容を手動で評価する。
  const scriptJsContent = fs.readFileSync(
    path.join(__dirname, "script.js"),
    "utf8"
  );
  window.eval(scriptJsContent);

  // script.js内のDOMContentLoadedリスナーが発火するよう、
  // イベントを明示的にディスパッチする（jsdomの自動発火に依存しない）
  document.dispatchEvent(new window.Event("DOMContentLoaded", { bubbles: true }));

  function setInputValue(id, value) {
    const el = document.getElementById(id);
    el.value = value;
    el.dispatchEvent(new window.Event("input"));
    el.dispatchEvent(new window.Event("change"));
  }

  function submitForm() {
    const form = document.getElementById("equipment-form");
    form.dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
  }

  let passCount = 0;
  let failCount = 0;

  function assert(condition, message) {
    if (condition) {
      passCount++;
      console.log("[PASS] " + message);
    } else {
      failCount++;
      console.error("[FAIL] " + message);
    }
  }

  // ------------------------------------------------------------
  // テスト1：通常の登録（車椅子・耐用年数6年）
  // ------------------------------------------------------------
  setInputValue("input-user-name", "テスト太郎");
  setInputValue("input-equipment-type", "wheelchair");
  setInputValue("input-decision-date", "2024-06-01");
  submitForm();

  let rows = document.querySelectorAll("#equipment-table-body tr");
  assert(rows.length === 1, "テスト1: 登録後に1行表示される");
  assert(
    document.getElementById("empty-state").style.display === "none",
    "テスト1: 空状態メッセージが非表示になる"
  );

  const firstRowCells = rows[0].querySelectorAll("td");
  assert(
    firstRowCells[3].textContent.trim() === "2030-06-01",
    "テスト1: 次回申請可能時期が交付決定日+6年（2030-06-01）で計算される（実際: " +
      firstRowCells[3].textContent.trim() + "）"
  );

  // ------------------------------------------------------------
  // テスト2：うるう年をまたぐケース（義肢・耐用年数5年、2024/2/29起点）
  // ------------------------------------------------------------
  setInputValue("input-user-name", "うるう年テスト");
  setInputValue("input-equipment-type", "gishi");
  setInputValue("input-decision-date", "2024-02-29");
  submitForm();

  rows = document.querySelectorAll("#equipment-table-body tr");
  assert(rows.length === 2, "テスト2: 2件目登録後、2行表示される");

  const leapRow = Array.from(rows).find((r) =>
    r.textContent.includes("うるう年テスト")
  );
  const leapCells = leapRow.querySelectorAll("td");
  // 2024-02-29 + 5年 = 2029年はうるう年ではないため、JSのDateは2029-03-01に繰り上がる
  assert(
    leapCells[3].textContent.trim() === "2029-03-01",
    "テスト2: うるう年2/29起点の+5年が2029-03-01に正しく繰り上がる（実際: " +
      leapCells[3].textContent.trim() + "）"
  );

  // ------------------------------------------------------------
  // テスト3：ダッシュボードの件数集計
  // ------------------------------------------------------------
  const dashTotal = document.getElementById("dash-total").textContent.trim();
  assert(dashTotal === "2", "テスト3: ダッシュボードの登録件数が2件になっている");

  // ------------------------------------------------------------
  // テスト4：削除機能
  // ------------------------------------------------------------
  const deleteButtons = document.querySelectorAll(".btn-delete");
  assert(deleteButtons.length === 2, "テスト4: 削除ボタンが2つ表示されている");

  // window.confirmをモックしてtrueを返すようにする
  window.confirm = () => true;
  deleteButtons[0].dispatchEvent(new window.Event("click", { bubbles: true }));

  rows = document.querySelectorAll("#equipment-table-body tr");
  assert(rows.length === 1, "テスト4: 削除後に1行だけ残っている");

  const dashTotalAfterDelete = document.getElementById("dash-total").textContent.trim();
  assert(
    dashTotalAfterDelete === "1",
    "テスト4: 削除後のダッシュボード件数が1件に更新される"
  );

  // ------------------------------------------------------------
  // テスト5：必須項目未入力時のバリデーション
  // ------------------------------------------------------------
  let alertMessage = null;
  window.alert = (msg) => {
    alertMessage = msg;
  };
  setInputValue("input-equipment-type", "");
  setInputValue("input-decision-date", "");
  submitForm();
  assert(
    alertMessage !== null && alertMessage.includes("必須"),
    "テスト5: 必須項目未入力でアラートが表示される（実際: " + alertMessage + "）"
  );

  rows = document.querySelectorAll("#equipment-table-body tr");
  assert(rows.length === 1, "テスト5: バリデーションエラー時は登録件数が増えない");

  // ------------------------------------------------------------
  // テスト6：残日数の緊急度クラス（危険：30日以内）
  // ------------------------------------------------------------
  const today = new Date();
  const soonDecision = new Date(today);
  soonDecision.setFullYear(soonDecision.getFullYear() - 5); // 歩行器:5年
  soonDecision.setDate(soonDecision.getDate() + 20); // 20日後に期限が来るよう調整
  const soonDateStr =
    soonDecision.getFullYear() +
    "-" +
    String(soonDecision.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(soonDecision.getDate()).padStart(2, "0");

  setInputValue("input-user-name", "緊急度テスト");
  setInputValue("input-equipment-type", "hokouki");
  setInputValue("input-decision-date", soonDateStr);
  submitForm();

  rows = document.querySelectorAll("#equipment-table-body tr");
  const urgentRow = Array.from(rows).find((r) =>
    r.textContent.includes("緊急度テスト")
  );
  assert(
    urgentRow.className.includes("row-urgency-danger"),
    "テスト6: 残り20日の登録が danger（危険）クラスになる（実際: " + urgentRow.className + "）"
  );

  // ------------------------------------------------------------
  // 結果サマリー
  // ------------------------------------------------------------
  console.log("\n========================================");
  console.log("PASS: " + passCount + " / FAIL: " + failCount);
  console.log("========================================");

  if (failCount > 0) {
    process.exit(1);
  }
}

run().catch((err) => {
  console.error("テスト実行中にエラーが発生しました:", err);
  process.exit(1);
});
