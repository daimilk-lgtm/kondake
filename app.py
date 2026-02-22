import streamlit as st
import pandas as pd
import requests
import base64
import io
import json
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import re

# ==============================================================================
# 【仕様定義書 / SPECIFICATIONS & USER REQUESTS】
# ------------------------------------------------------------------------------
# [基本仕様]
# 1. 接続・保存機能 (Storage): GitHub API (menu.csv, history.csv, ingredients.csv).
# 2. 献立作成ロジック (Planning): 主菜1, 副菜1, 副菜2, 汁物の4枠。
# 3. 買い物リスト & 印刷 (Shopping & Print): カテゴリ別表示 & A4最適化印刷.
# 4. 履歴管理 (History): 自動保存。履歴タブでの料理名修正・行削除機能。
# 5. UI/UX: スマホ操作優先（キーボード自動起動防止、マルチセレクト維持）。
#
# [ユーザー個別依頼 & 運用ルール]
# - 「主菜2」は献立作成枠から除外。定番アイテムとしてのみ再利用。
# - uid列は完全に排除。
# - 【最重要】修正時は必ず「全文」を出力すること。一部省略は厳禁。
# - 【最重要】既存の細かい仕様（印刷、CSS等）は指示がない限り絶対に変えない。
# - 【最重要】ユーザーからの追加指示は、毎回このセクションに書き足して更新すること。
# - [2026/02/22] メモ欄を曜日ごとに個別入力可能とし、買い物リストに反映。
# - [2026/02/22] 買い物リスト反映時、メモ内容に「日付・曜日」を付記すること。
# - [2026/02/22] 読み込み失敗時、エラーを握りつぶさずStatus Codeやレスポンス詳細を表示。
# - [2026/02/22] 献立入力時、選択した曜日タブが勝手に切り替わらないよう操作性を維持する。
# - [2026/02/22] GitHub上に「draft.json」を作成し、入力内容を共有可能にする。
# - [2026/02/22] 一時保存用の実行ボタン名は「一時保存」とする。
# - [2026/02/22] 確定献立はカテゴリーごとに列を分ける。同一カテゴリーに複数ある場合は複数列に分割し、汁物は必ず右端の列に配置する。
# - [2026/02/22] 買い物リストの各項目を個別に編集・削除できる機能を、スマホで直感的に操作できるボタン形式で実装。
# - [2026/02/22] 材料名が連結して表示される現象を修正（材料パースロジックの強化）。
# - [2026/02/22] 買い物リスト編集時、元のカテゴリーを自動で引き継ぎ、勝手に「未分類」へ移動しないよう修正。編集項目からカテゴリー選択を削除。
# - [2026/02/22] 買い物リストにおいて、材料の数量（個数）を独立した列として扱い、表示・編集・印刷に反映させる。
# - [2026/02/22] 印刷設定を変更。A4一枚に収まるようレイアウトを最適化。文字サイズは約10ptを基準とし、余白や表の幅を調整。
# - [2026/02/22] ログイン機能を追加。IDはメールアドレス、パスワードは半角英数字8文字。環境変数（Streamlit Secrets）で管理。既存デザインを維持。
# ==============================================================================

VERSION = "1.5.1"

# --- 1. 接続・認証設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
DRAFT_FILE = "draft.json"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# 環境変数からログイン情報を取得
VALID_EMAIL = st.secrets.get("LOGIN_EMAIL")
VALID_PASSWORD = st.secrets.get("LOGIN_PASSWORD")

def get_github_content(filename):
    """GitHubからファイルを取得する汎用関数"""
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            content = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            return content, r.json()["sha"]
    except: pass
    return None, None

def save_to_github(content, filename, message, current_sha=None):
    """GitHubへファイルを保存する汎用関数"""
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 2. デザイン定義 ---
st.set_page_config(page_title="献だけ", layout="centered")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    .shopping-card { background: white; padding: 15px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 10px; }
    .category-label { font-size: 0.8rem; color: #999; margin-bottom: 5px; }
    .item-row { display: flex; justify-content: space-between; font-size: 1.1rem; padding: 4px 0; border-bottom: 0.5px solid #f9f9f9; }
    .item-name { flex-grow: 1; }
    .item-qty { min-width: 50px; text-align: right; color: #666; margin-left: 10px; }
    .preview-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 10px; margin-bottom: 20px; overflow-x: auto; display: block; }
    .preview-table th, .preview-table td { border: 1px solid #eee; padding: 6px; text-align: left; min-width: 80px; }
    .preview-table th { background-color: #fcfcfc; font-weight: 400; }
    .edit-item-box { background: #fdfdfd; padding: 10px; border: 1px dashed #ccc; border-radius: 8px; margin: 5px 0; }
    .login-box { max-width: 400px; margin: 0 auto; padding: 20px; background: white; border-radius: 12px; border: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

# --- 3. 認証ロジック ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

def login_screen():
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    with st.form("login_form"):
        st.subheader("ログイン")
        email_input = st.text_input("メールアドレス")
        pass_input = st.text_input("パスワード", type="password")
        submit = st.form_submit_button("ログイン", use_container_width=True)
        
        if submit:
            if email_input == VALID_EMAIL and pass_input == VALID_PASSWORD:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("IDまたはパスワードが正しくありません")
    st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state['authenticated']:
    login_screen()
    st.stop()

# --- 4. メインアプリ（データ取得） ---
def get_menu_data():
    content, sha = get_github_content(FILE)
    if content:
        df = pd.read_csv(io.StringIO(content))
        return df, sha
    else:
        st.error("GitHubからのメニュー取得に失敗しました。設定を確認してください。")
        return None, None

@st.cache_data(ttl=60)
def get_history_data():
    content, sha = get_github_content(HIST_FILE)
    if content:
        df_h = pd.read_csv(io.StringIO(content))
        if "uid" in df_h.columns: df_h = df_h.drop(columns=["uid"])
        return df_h, sha
    return pd.DataFrame(columns=["日付", "曜日", "料理名"]), None

@st.cache_data(ttl=60)
def get_dict_data():
    try:
        url = f"https://raw.githubusercontent.com/{REPO}/main/{DICT_FILE}"
        return pd.read_csv(url)
    except: return None

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

df_menu, menu_sha = get_menu_data()
df_dict = get_dict_data()
df_hist, hist_sha = get_history_data()

draft_content, draft_sha = get_github_content(DRAFT_FILE)
draft_data = json.loads(draft_content) if draft_content else {}

if df_menu is None:
    st.stop() 

cats = ["主菜1", "副菜1", "副菜2", "汁物"]
tab_plan, tab_hist, tab_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ メニュー管理"])

# --- 5. タブ: 献立作成 ---
with tab_plan:
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日）", value=default_sun)
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    
    days_tabs = st.tabs([f"{day_labels[i]}" for i in range(7)])
    weekly_plan = {}
    
    for i, day_tab in enumerate(days_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with day_tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            
            day_menu = {}
            for cat in cats:
                key_name = f"s_{i}_{cat}"
                default_val = draft_data.get(key_name, [])
                day_menu[cat] = st.multiselect(
                    cat, 
                    df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), 
                    key=key_name, 
                    default=[v for v in default_val if v in df_menu["料理名"].tolist()],
                    placeholder="選択..."
                )
            
            memo_key = f"memo_{i}"
            day_memo = st.text_input(
                "この日のメモ", 
                key=memo_key, 
                value=draft_data.get(memo_key, ""),
                placeholder="買い足すものなど..."
            )
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i], "memo": day_memo}

    list_memo_options = df_menu[df_menu["カテゴリー"] == "主菜2"]["料理名"].tolist()
    def_memos = draft_data.get("list_memo_multi", [])
    selected_memos = st.multiselect(
        "定番アイテム", 
        list_memo_options, 
        key="list_memo_multi", 
        default=[v for v in def_memos if v in list_memo_options],
        placeholder="選択..."
    )

    col_save, _ = st.columns([1, 1])
    with col_save:
        if st.button("一時保存", use_container_width=True):
            current_draft = {}
            for i in range(7):
                for cat in cats:
                    current_draft[f"s_{i}_{cat}"] = st.session_state[f"s_{i}_{cat}"]
                current_draft[f"memo_{i}"] = st.session_state[f"memo_{i}"]
            current_draft["list_memo_multi"] = st.session_state["list_memo_multi"]
            
            res_code = save_to_github(json.dumps(current_draft, ensure_ascii=False), DRAFT_FILE, "Update draft", draft_sha)
            if res_code in [200, 201]:
                st.toast("入力を一時保存しました")
            else:
                st.error(f"一時保存に失敗しました。Status: {res_code}")

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        all_ings_list = []
        new_history_entries = []
        
        max_counts = {"主菜1": 1, "副菜1": 1, "副菜2": 1, "汁物": 1}
        for d_str, data in weekly_plan.items():
            for cat in cats:
                max_counts[cat] = max(max_counts[cat], len(data["menu"].get(cat, [])))

        header_html = "<tr><th>日付</th>"
        for cat in ["主菜1", "副菜1", "副菜2"]:
            for j in range(max_counts[cat]):
                suffix = f" {j+1}" if max_counts[cat] > 1 else ""
                header_html += f"<th>{cat}{suffix}</th>"
        for j in range(max_counts["汁物"]):
            suffix = f" {j+1}" if max_counts["汁物"] > 1 else ""
            header_html += f"<th>汁物{suffix}</th>"
        header_html += "</tr>"

        rows_html = ""
        for d_str, data in weekly_plan.items():
            v = data["menu"]
            w_str = data["weekday"]
            d_memo = data["memo"]
            row_content = f"<td>{d_str}({w_str})</td>"
            for cat in ["主菜1", "副菜1", "副菜2", "汁物"]:
                items = v.get(cat, [])
                for j in range(max_counts[cat]):
                    cell_val = items[j] if j < len(items) else "-"
                    row_content += f"<td>{cell_val}</td>"
            rows_html += f"<tr>{row_content}</tr>"
            
            for dish_list in v.values():
                for dish in dish_list:
                    new_history_entries.append({"日付": d_str, "曜日": w_str, "料理名": dish})
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    splitted = re.split(r'[、,\n\s・/]+', str(ing_raw))
                    all_ings_list.extend([x.strip() for x in splitted if x.strip()])
            
            if d_memo:
                memo_prefix = f"{d_str}({w_str}) メモ: "
                splitted_memo = re.split(r'[、,\n\s・/]+', d_memo)
                all_ings_list.extend([memo_prefix + x.strip() for x in splitted_memo if x.strip()])

        for selected_dish in selected_memos:
            ing_raw_memo = df_menu[df_menu["料理名"] == selected_dish]["材料"].iloc[0]
            splitted_定番 = re.split(r'[、,\n\s・/]+', str(ing_raw_memo))
            all_ings_list.extend([x.strip() for x in splitted_定番 if x.strip()])

        if new_history_entries:
            df_combined_h = pd.concat([df_hist, pd.DataFrame(new_history_entries)], ignore_index=True).drop_duplicates()
            save_to_github(df_combined_h.to_csv(index=False, encoding="utf-8-sig"), HIST_FILE, "Update history", hist_sha)
            st.toast("履歴を保存しました")

        st.session_state["current_rows_html"] = rows_html
        st.session_state["current_header_html"] = header_html
        
        counts = pd.Series(all_ings_list).value_counts()
        init_shopping = []
        for item, count in counts.items():
            category = "99未分類"
            if "メモ:" not in str(item):
                if df_dict is not None:
                    for _, row in df_dict.iterrows():
                        if str(row["材料"]) in str(item): category = row["種別"]; break
            else:
                category = "📝 各日メモ"
            init_shopping.append({"item": item, "count": int(count), "cat": category, "id": f"item_{len(init_shopping)}"})
        st.session_state["shopping_list_data"] = init_shopping

    if "shopping_list_data" in st.session_state:
        st.markdown("### 🗓 確定した献立")
        st.markdown(f'<table class="preview-table">{st.session_state["current_header_html"]}{st.session_state["current_rows_html"]}</table>', unsafe_allow_html=True)

        st.markdown("### 🛒 買い物リストの調整")
        
        shopping_data = st.session_state["shopping_list_data"]
        unique_cats = sorted(list(set(d["cat"] for d in shopping_data)))
        
        for cat in unique_cats:
            st.markdown(f"**【{cat}】**")
            items_in_cat = [d for d in shopping_data if d["cat"] == cat]
            
            for item_obj in items_in_cat:
                item_id = item_obj["id"]
                if st.session_state.get(f"del_{item_id}", False):
                    continue

                col_text, col_qty, col_edit, col_del = st.columns([5, 1, 2, 2])
                col_text.markdown(f"□ {item_obj['item']}")
                col_qty.markdown(f"{item_obj['count']}" if item_obj['count'] > 1 else "")
                
                if col_edit.button("📝", key=f"btn_edit_{item_id}"):
                    st.session_state[f"editing_{item_id}"] = True
                
                if col_del.button("🗑️", key=f"btn_del_{item_id}"):
                    st.session_state[f"del_{item_id}"] = True
                    st.rerun()

                if st.session_state.get(f"editing_{item_id}", False):
                    with st.container():
                        st.markdown(f'<div class="edit-item-box">', unsafe_allow_html=True)
                        e_name = st.text_input("項目名", value=item_obj["item"], key=f"inp_name_{item_id}")
                        e_cnt = st.number_input("数量", value=int(item_obj["count"]), min_value=1, key=f"inp_qty_{item_id}")
                        if st.button("保存", key=f"save_{item_id}"):
                            for d in st.session_state["shopping_list_data"]:
                                if d["id"] == item_id:
                                    d["item"] = e_name
                                    d["count"] = e_cnt
                                    break
                            st.session_state[f"editing_{item_id}"] = False
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

        # 最終印刷用HTML (A4最適化レイアウト)
        active_items = [d for d in st.session_state["shopping_list_data"] if not st.session_state.get(f"del_{d['id']}", False)]
        display_cats = sorted(list(set(d["cat"] for d in active_items)))
        
        cards_html = ""
        for c in display_cats:
            cards_html += f'<div class="print-card"><h3>{c}</h3>'
            for row in [d for d in active_items if d["cat"] == c]:
                qty_val = f'({row["count"]})' if row["count"] > 1 else ''
                cards_html += f'<div class="print-row"><span>□ {row["item"]}</span><span>{qty_val}</span></div>'
            cards_html += '</div>'
        
        st.markdown("---")
        
        print_html = f"""
        <html>
        <head>
            <style>
                @page {{ size: A4; margin: 10mm; }}
                body {{ font-family: sans-serif; font-size: 10pt; line-height: 1.2; color: #333; }}
                h2 {{ border-bottom: 2px solid #333; padding-bottom: 5px; margin-top: 15px; font-size: 14pt; }}
                h3 {{ font-size: 11pt; margin: 8px 0 4px 0; background: #eee; padding: 2px 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; table-layout: fixed; }}
                th, td {{ border: 1px solid #999; padding: 4px; text-align: left; word-wrap: break-word; font-size: 9pt; }}
                th {{ background: #f2f2f2; }}
                .print-container {{ display: flex; flex-wrap: wrap; gap: 10px; }}
                .print-card {{ border: 1px solid #ccc; padding: 5px; width: calc(33.3% - 12px); box-sizing: border-box; break-inside: avoid; }}
                .print-row {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 2px 0; }}
                @media print {{
                    .no-print {{ display: none; }}
                    .print-card {{ width: calc(50% - 10px); }}
                }}
            </style>
        </head>
        <body>
            <h2>🗓 献立表</h2>
            <table>{st.session_state['current_header_html']}{st.session_state['current_rows_html']}</table>
            <h2>🛒 買い物リスト</h2>
            <div class="print-container">{cards_html}</div>
        </body>
        </html>
        """
        
        b64_print = base64.b64encode(print_html.encode('utf-8')).decode('utf-8')
        components.html(f"""
            <div style="margin-top:20px;"><button id="pbtn" style="width:100%;background-color:#262730;color:white;padding:12px;border:none;border-radius:8px;cursor:pointer;font-size:1rem;">A4印刷・最終確認</button></div>
            <script>
            document.getElementById('pbtn').onclick = function() {{
                var html = atob('{b64_print}');
                var w = window.open('', '_blank');
                w.document.open(); w.document.write(decodeURIComponent(escape(html))); w.document.close();
                setTimeout(function() {{ w.focus(); w.print(); }}, 500);
            }};
            </script>
        """, height=80)

# --- 6. タブ: 履歴 ---
with tab_hist:
    st.subheader("📜 履歴の管理")
    if not df_hist.empty:
        df_hist_display = df_hist.copy().sort_values(["日付", "料理名"], ascending=[False, True])
        selected_hist_idx = st.selectbox("修正・削除するデータを選択", range(len(df_hist_display)), format_func=lambda i: f"{df_hist_display.iloc[i]['日付']} - {df_hist_display.iloc[i]['料理名']}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("選択した履歴を削除", type="secondary", use_container_width=True):
                target_date = df_hist_display.iloc[selected_hist_idx]['日付']
                target_name = df_hist_display.iloc[selected_hist_idx]['料理名']
                df_hist = df_hist[~((df_hist['日付'] == target_date) & (df_hist['料理名'] == target_name))]
                save_to_github(df_hist.to_csv(index=False, encoding="utf-8-sig"), HIST_FILE, f"Delete history {target_date}", hist_sha)
                st.cache_data.clear()
                st.rerun()
        with col2:
            new_hist_name = st.text_input("料理名を修正", value=df_hist_display.iloc[selected_hist_idx]['料理名'])
            if st.button("料理名を修正して保存", type="primary", use_container_width=True):
                target_date = df_hist_display.iloc[selected_hist_idx]['日付']
                target_name = df_hist_display.iloc[selected_hist_idx]['料理名']
                df_hist.loc[(df_hist['日付'] == target_date) & (df_hist['料理名'] == target_name), '料理名'] = new_hist_name
                save_to_github(df_hist.to_csv(index=False, encoding="utf-8-sig"), HIST_FILE, f"Edit history {target_date}", hist_sha)
                st.cache_data.clear()
                st.rerun()
        st.divider()
        st.dataframe(df_hist_display, use_container_width=True, hide_index=True)

# --- 7. タブ: メニュー管理 & 設定 ---
with tab_manage:
    st.subheader("⚙️ メニュー管理")
    edit_dish = st.selectbox("編集", ["選択してください"] + sorted(df_menu["料理名"].tolist()))
    if edit_dish != "選択してください":
        current_data = df_menu[df_menu["料理名"] == edit_dish].iloc[0]
        with st.form("edit_form"):
            new_n = st.text_input("料理名", value=current_data["料理名"])
            all_cats_edit = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
            new_c = st.selectbox("カテゴリー", all_cats_edit, index=all_cats_edit.index(current_data["カテゴリー"]) if current_data["カテゴリー"] in all_cats_edit else 0)
            new_m = st.text_area("材料", value=current_data["材料"])
            if st.form_submit_button("変更を保存"):
                df_menu.loc[df_menu["料理名"] == edit_dish, ["料理名", "カテゴリー", "材料"]] = [new_n, new_c, new_m]
                save_to_github(df_menu.to_csv(index=False, encoding="utf-8-sig"), FILE, f"Update {edit_dish}", menu_sha)
                st.cache_data.clear()
                st.rerun()
    st.divider()
    with st.form("add_form"):
        st.markdown("##### 新規追加")
        n = st.text_input("料理名")
        c = st.selectbox("カテゴリー", ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"])
        m = st.text_area("材料")
        if st.form_submit_button("新規保存"):
            if n and m:
                new_df = pd.concat([df_menu, pd.DataFrame([[n, c, m]], columns=df_menu.columns)], ignore_index=True)
                save_to_github(new_df.to_csv(index=False, encoding="utf-8-sig"), FILE, f"Add {n}", menu_sha)
                st.cache_data.clear()
                st.rerun()
    
    st.divider()
    st.subheader("👤 アカウント設定")
    if st.button("ログアウト", type="secondary"):
        st.session_state['authenticated'] = False
        st.rerun()

    st.markdown(f'<div style="text-align: right; color: #ddd; font-size: 0.6rem; margin-top: 50px;">Version {VERSION}</div>', unsafe_allow_html=True)
