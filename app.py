import streamlit as st
import pandas as pd
import io
import json
import base64
import re
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# 各自作成したモジュールをインポート
from github_utils import get_github_content, save_to_github
from auth_module import login_screen, show_auth_header

# ==============================================================================
# 【仕様定義書 / SPECIFICATIONS & USER REQUESTS】
# ------------------------------------------------------------------------------
# [基本仕様]
# 1. 接続・保存機能: GitHub API (menu.csv, history.csv, ingredients.csv, draft.json, users.json).
# 2. 献立作成: 主菜1, 副菜1, 副菜2, 汁物の4枠。主菜2は定番用。
# 3. 買い物リスト: カテゴリ別表示 & A4最適化印刷。
# 4. 履歴管理: ユーザー別に保存。修正・削除機能。
# 5. UI/UX: スマホ優先。シングルカラム構成（サイドバー廃止）。
#
# [運用ルール]
# - [2026/02/22] 物理分割導入: app.py, auth_module.py, github_utils.py。
# - [2026/02/22] 全文作成のルールは「各ファイル単位での全文作成」とする。
# - [2026/02/22] 修正時はAIが段階的プロンプトを作成し、ユーザーが順次適用する。
# ==============================================================================

VERSION = "1.7.1"
FILE = "menu.csv"
HIST_FILE = "history.csv"
DRAFT_FILE = "draft.json"

st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")

# デザイン定義（CSS）
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    [data-testid="stSidebar"] { display: none; }
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0 20px 0; letter-spacing: 0.5rem; }
    .auth-header { position: absolute; top: -10px; right: 0; text-align: right; padding: 10px; z-index: 1000; }
    .user-id { font-size: 0.75rem; color: #666; }
    .preview-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 10px; margin-bottom: 20px; overflow-x: auto; display: block; }
    .preview-table th, .preview-table td { border: 1px solid #eee; padding: 6px; text-align: left; min-width: 80px; }
    .preview-table th { background-color: #fcfcfc; font-weight: 400; }
    .edit-item-box { background: #fdfdfd; padding: 10px; border: 1px dashed #ccc; border-radius: 8px; margin: 5px 0; }
</style>
""", unsafe_allow_html=True)

# 認証チェック
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    login_screen()
    st.stop()

# ログイン後のヘッダー表示
show_auth_header()
st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

# データ取得
def load_all_data():
    m_content, m_sha = get_github_content(FILE)
    h_content, h_sha = get_github_content(HIST_FILE)
    d_content, d_sha = get_github_content(DRAFT_FILE)
    
    df_menu = pd.read_csv(io.StringIO(m_content)) if m_content else None
    df_hist = pd.read_csv(io.StringIO(h_content)) if h_content else pd.DataFrame(columns=["日付", "曜日", "料理名", "user"])
    if "user" not in df_hist.columns: df_hist["user"] = "unknown"
    
    draft_data = json.loads(d_content) if d_content else {}
    return df_menu, m_sha, df_hist, h_sha, draft_data, d_sha

df_menu, menu_sha, df_hist, hist_sha, draft_data, draft_sha = load_all_data()
if df_menu is None: st.stop()

# タブ構成
tab_plan, tab_hist, tab_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ 管理"])

with tab_plan:
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    start_date = st.date_input("開始日（日）", value=today - timedelta(days=offset))
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    days_tabs = st.tabs(day_labels)
    weekly_plan = {}
    cats = ["主菜1", "副菜1", "副菜2", "汁物"]

    for i, day_tab in enumerate(days_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with day_tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            day_menu = {}
            for cat in cats:
                k = f"s_{i}_{cat}"
                def_v = draft_data.get(k, [])
                day_menu[cat] = st.multiselect(cat, df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), 
                                               key=k, default=[v for v in def_v if v in df_menu["料理名"].tolist()])
            m_k = f"memo_{i}"
            day_memo = st.text_input("メモ", key=m_k, value=draft_data.get(m_k, ""))
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i], "memo": day_memo}

    list_memo_options = df_menu[df_menu["カテゴリー"] == "主菜2"]["料理名"].tolist()
    selected_memos = st.multiselect("定番アイテム", list_memo_options, key="list_memo_multi", 
                                    default=[v for v in draft_data.get("list_memo_multi", []) if v in list_memo_options])

    if st.button("一時保存", use_container_width=True):
        cur_draft = {f"s_{i}_{cat}": st.session_state[f"s_{i}_{cat}"] for i in range(7) for cat in cats}
        for i in range(7): cur_draft[f"memo_{i}"] = st.session_state[f"memo_{i}"]
        cur_draft["list_memo_multi"] = st.session_state["list_memo_multi"]
        save_to_github(json.dumps(cur_draft, ensure_ascii=False), DRAFT_FILE, "Update draft", draft_sha)
        st.toast("保存完了")

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        all_ings_list = []
        new_history_entries = []
        max_counts = {c: 1 for c in cats}
        for d in weekly_plan.values():
            for c in cats: max_counts[c] = max(max_counts[c], len(d["menu"].get(c, [])))

        header_html = "<tr><th>日付</th>" + "".join([f"<th>{c}</th>" for c in cats]) + "</tr>"
        rows_html = ""
        for d_str, data in weekly_plan.items():
            row_content = f"<td>{d_str}({data['weekday']})</td>"
            for c in cats:
                items = data["menu"].get(c, [])
                row_content += f"<td>{items[0] if items else '-'}</td>"
            rows_html += f"<tr>{row_content}</tr>"
            for dish_list in data["menu"].values():
                for dish in dish_list:
                    new_history_entries.append({"日付": d_str, "曜日": data["weekday"], "料理名": dish, "user": st.session_state['user_email']})
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    all_ings_list.extend([x.strip() for x in re.split(r'[、,\n\s・/]+', str(ing_raw)) if x.strip()])
            if data["memo"]:
                all_ings_list.extend([f"{d_str}メモ: " + x.strip() for x in re.split(r'[、,\n\s・/]+', data["memo"]) if x.strip()])

        for m_dish in selected_memos:
            all_ings_list.extend([x.strip() for x in re.split(r'[、,\n\s・/]+', str(df_menu[df_menu["料理名"] == m_dish]["材料"].iloc[0])) if x.strip()])

        if new_history_entries:
            df_combined_h = pd.concat([df_hist, pd.DataFrame(new_history_entries)], ignore_index=True).drop_duplicates()
            save_to_github(df_combined_h.to_csv(index=False, encoding="utf-8-sig"), HIST_FILE, "Update history", hist_sha)

        st.session_state["current_rows_html"] = rows_html
        st.session_state["current_header_html"] = header_html
        
        counts = pd.Series(all_ings_list).value_counts()
        init_shopping = [{"item": item, "count": int(count), "cat": "未分類", "id": f"it_{i}"} for i, (item, count) in enumerate(counts.items())]
        st.session_state["shopping_list_data"] = init_shopping

    if "shopping_list_data" in st.session_state:
        st.markdown(f'<table class="preview-table">{st.session_state["current_header_html"]}{st.session_state["current_rows_html"]}</table>', unsafe_allow_html=True)
        for item_obj in st.session_state["shopping_list_data"]:
            if st.session_state.get(f"del_{item_obj['id']}", False): continue
            st.write(f"□ {item_obj['item']} ({item_obj['count']})")

with tab_hist:
    st.subheader("📜 あなたの履歴")
    u_hist = df_hist[df_hist["user"] == st.session_state['user_email']]
    st.dataframe(u_hist.drop(columns=["user"]), use_container_width=True, hide_index=True)

with tab_manage:
    st.subheader("⚙️ メニュー管理")
    st.write(f"Version {VERSION}")
