import streamlit as st
import pandas as pd
import io
import json
import base64
import re
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# 外部モジュール読み込み
try:
    from github_utils import get_github_content, save_to_github
    from auth_module import login_screen, show_auth_header
except ImportError:
    st.error("モジュール読み込みエラー。ファイル構成を確認してください。")
    st.stop()

# ==============================================================================
# 【仕様定義書 / SPECIFICATIONS & USER REQUESTS】
# ------------------------------------------------------------------------------
# [基本仕様]
# 1. 接続・保存機能: GitHub API (menu.csv, history.csv, ingredients.csv, draft.json, users.json).
# 2. 献立作成: 主菜1, 副菜1, 副菜2, 汁物の4枠。
# 3. 買い物リスト: 個別編集・削除機能、数量管理、カテゴリ自動分類。
# 4. 印刷: A4最適化レイアウト印刷ボタン。
# 5. 履歴管理: ユーザー別に保存。修正・削除機能。
# 6. UI/UX: スマホ優先。シングルカラム構成。右上にログインID表示。
#
# [運用ルール]
# - [2026/02/22] 物理分割導入: app.py, auth_module.py, github_utils.py。
# - [2026/02/22] 買い物リストの個別編集・削除・数量・A4印刷仕様を完全復元。
# - [2026/02/22] 買い物リストの名称を「買い物リスト」に統一。
# - [2026/02/22] 全文作成のルールは「各ファイル単位での全文作成」とする。
# - [2026/02/22] 修正時はAIが段階的プロンプトを作成し、ユーザーが順次適用する。
# - [2026/02/22] 買い物リストのモバイル表示を最適化。フォントとボタンを小型化し横一行を死守。
# ==============================================================================

VERSION = "1.7.6"
FILE = "menu.csv"
HIST_FILE = "history.csv"
DRAFT_FILE = "draft.json"
DICT_FILE = "ingredients.csv"

st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")

# デザイン定義
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
    
    /* 買い物リストのモバイル最適化 (一行死守) */
    .shopping-item-text {
        font-size: 0.85rem !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
    }
    .shopping-count-text {
        font-size: 0.8rem !important;
        color: #666;
    }
    
    [data-testid="column"] {
        flex: 0 1 auto !important;
        min-width: 0px !important;
    }
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 0.2rem !important; /* 間隔を狭める */
    }
    /* ボタンを極小化 */
    div[data-testid="stHorizontalBlock"] button {
        padding: 0px 2px !important;
        min-height: 24px !important;
        max-height: 24px !important;
        font-size: 0.7rem !important;
        line-height: 1 !important;
        width: 32px !important;
    }
</style>
""", unsafe_allow_html=True)

if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if not st.session_state['authenticated']:
    login_screen()
    st.stop()

show_auth_header()
st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

# データ取得
@st.cache_data(ttl=60)
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

try:
    dict_url = f"https://raw.githubusercontent.com/daimilk-lgtm/kondake/main/{DICT_FILE}"
    df_dict = pd.read_csv(dict_url)
except: df_dict = None

if df_menu is None: st.stop()

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

        header_html = "<tr><th>日付</th>"
        for c in ["主菜1", "副菜1", "副菜2", "汁物"]:
            for j in range(max_counts[c]):
                header_html += f"<th>{c}{f' {j+1}' if max_counts[c]>1 else ''}</th>"
        header_html += "</tr>"

        rows_html = ""
        for d_str, data in weekly_plan.items():
            row_content = f"<td>{d_str}({data['weekday']})</td>"
            for c in ["主菜1", "副菜1", "副菜2", "汁物"]:
                items = data["menu"].get(c, [])
                for j in range(max_counts[c]):
                    row_content += f"<td>{items[j] if j < len(items) else '-'}</td>"
            rows_html += f"<tr>{row_content}</tr>"
            
            for dish_list in data["menu"].values():
                for dish in dish_list:
                    new_history_entries.append({"日付": d_str, "曜日": data["weekday"], "料理名": dish, "user": st.session_state['user_email']})
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    all_ings_list.extend([x.strip() for x in re.split(r'[、,\n\s・/]+', str(ing_raw)) if x.strip()])
            if data["memo"]:
                all_ings_list.extend([f"{d_str}({data['weekday']}) メモ: " + x.strip() for x in re.split(r'[、,\n\s・/]+', data["memo"]) if x.strip()])

        for m_dish in selected_memos:
            all_ings_list.extend([x.strip() for x in re.split(r'[、,\n\s・/]+', str(df_menu[df_menu["料理名"] == m_dish]["材料"].iloc[0])) if x.strip()])

        if new_history_entries:
            df_combined_h = pd.concat([df_hist, pd.DataFrame(new_history_entries)], ignore_index=True).drop_duplicates()
            save_to_github(df_combined_h.to_csv(index=False, encoding="utf-8-sig"), HIST_FILE, "Update history", hist_sha)

        st.session_state["current_rows_html"] = rows_html
        st.session_state["current_header_html"] = header_html
        counts = pd.Series(all_ings_list).value_counts()
        init_shopping = []
        for i, (item, count) in enumerate(counts.items()):
            cat = "99未分類"
            if "メモ:" in str(item): cat = "📝 各日メモ"
            elif df_dict is not None:
                for _, r in df_dict.iterrows():
                    if str(r["材料"]) in str(item): cat = r["種別"]; break
            init_shopping.append({"item": item, "count": int(count), "cat": cat, "id": f"it_{i}"})
        st.session_state["shopping_list_data"] = init_shopping

    if "shopping_list_data" in st.session_state:
        st.markdown("### 🗓 確定した献立")
        st.markdown(f'<table class="preview-table">{st.session_state["current_header_html"]}{st.session_state["current_rows_html"]}</table>', unsafe_allow_html=True)
        
        st.markdown("### 🛒 買い物リスト")
        s_data = st.session_state["shopping_list_data"]
        u_cats = sorted(list(set(d["cat"] for d in s_data)))
        
        for c in u_cats:
            st.markdown(f"**【{c}】**")
            for item_obj in [d for d in s_data if d["cat"] == c]:
                i_id = item_obj["id"]
                if st.session_state.get(f"del_{i_id}", False): continue
                
                # 比率を [10, 2, 2, 2] に変更し、材料名を優先
                c1, c2, c3, c4 = st.columns([10, 2, 2, 2])
                c1.markdown(f'<span class="shopping-item-text">□ {item_obj["item"]}</span>', unsafe_allow_html=True)
                c2.markdown(f'<span class="shopping-count-text">{item_obj["count"] if item_obj["count"] > 1 else ""}</span>', unsafe_allow_html=True)
                if c3.button("📝", key=f"ed_{i_id}"): st.session_state[f"edit_{i_id}"] = True
                if c4.button("🗑️", key=f"dl_{i_id}"): 
                    st.session_state[f"del_{i_id}"] = True
                    st.rerun()

                if st.session_state.get(f"edit_{i_id}", False):
                    with st.container():
                        st.markdown('<div class="edit-item-box">', unsafe_allow_html=True)
                        en = st.text_input("名称", value=item_obj["item"], key=f"in_n_{i_id}")
                        ec = st.number_input("数", value=int(item_obj["count"]), min_value=1, key=f"in_q_{i_id}")
                        if st.button("保存", key=f"sv_{i_id}"):
                            for d in st.session_state["shopping_list_data"]:
                                if d["id"] == i_id: d["item"], d["count"] = en, ec; break
                            st.session_state[f"edit_{i_id}"] = False
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

        active = [d for d in st.session_state["shopping_list_data"] if not st.session_state.get(f"del_{d['id']}", False)]
        cards_html = "".join([f'<div class="print-card"><h3>{c}</h3>' + "".join([f'<div class="print-row"><span>□ {r["item"]}</span><span>{f"({r["count"]})" if r["count"]>1 else ""}</span></div>' for r in active if r["cat"]==c]) + '</div>' for c in sorted(list(set(d["cat"] for d in active)))])
        print_html = f"""<html><head><style>@page {{ size: A4; margin: 10mm; }} body {{ font-family: sans-serif; font-size: 10pt; }} h2 {{ border-bottom: 2px solid #333; }} .print-container {{ display: flex; flex-wrap: wrap; gap: 10px; }} .print-card {{ border: 1px solid #ccc; padding: 5px; width: calc(50% - 10px); break-inside: avoid; }} .print-row {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; }}</style></head><body><h2>🗓 献立表</h2><table>{st.session_state.get('current_header_html','')}{st.session_state.get('current_rows_html','')}</table><h2>🛒 買い物リスト</h2><div class="print-container">{cards_html}</div></body></html>"""
        b64 = base64.b64encode(print_html.encode('utf-8')).decode('utf-8')
        components.html(f'<button id="pb" style="width:100%;background:#262730;color:white;padding:12px;border:none;border-radius:8px;cursor:pointer;">A4印刷・最終確認</button><script>document.getElementById("pb").onclick=function(){{var w=window.open();w.document.write(atob("{b64}"));w.document.close();w.print();}};</script>', height=60)

with tab_hist:
    st.subheader("📜 あなたの履歴")
    u_hist = df_hist[df_hist["user"] == st.session_state['user_email']]
    if not u_hist.empty:
        disp = u_hist.copy().sort_values(["日付", "料理名"], ascending=[False, True])
        sel_idx = st.selectbox("データ選択", range(len(disp)), format_func=lambda i: f"{disp.iloc[i]['日付']} - {disp.iloc[i]['料理名']}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("削除", use_container_width=True):
                df_hist = df_hist[~((df_hist['日付']==disp.iloc[sel_idx]['日付'])&(df_hist['料理名']==disp.iloc[sel_idx]['料理名'])&(df_hist['user']==st.session_state['user_email']))]
                save_to_github(df_hist.to_csv(index=False, encoding="utf-8-sig"), HIST_FILE, "Del hist", hist_sha)
                st.cache_data.clear(); st.rerun()
        with c2:
            new_name = st.text_input("修正名", value=disp.iloc[sel_idx]['料理名'])
            if st.button("修正保存", use_container_width=True):
                df_hist.loc[(df_hist['日付']==disp.iloc[sel_idx]['日付'])&(df_hist['料理名']==disp.iloc[sel_idx]['料理名'])&(df_hist['user']==st.session_state['user_email']), '料理名'] = new_name
                save_to_github(df_hist.to_csv(index=False, encoding="utf-8-sig"), HIST_FILE, "Edit hist", hist_sha)
                st.cache_data.clear(); st.rerun()
        st.dataframe(disp.drop(columns=["user"]), use_container_width=True, hide_index=True)
    else: st.info("履歴がありません")

with tab_manage:
    st.subheader("⚙️ メニュー編集")
    edit_dish = st.selectbox("既存メニュー選択", ["未選択"] + sorted(df_menu["料理名"].tolist()))
    if edit_dish != "未選択":
        cur = df_menu[df_menu["料理名"] == edit_dish].iloc[0]
        with st.form("ed_menu"):
            nn = st.text_input("料理名", value=cur["料理名"]); nc = st.selectbox("カテゴリ", ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"], index=["主菜1", "主菜2", "副菜1", "副菜2", "汁物"].index(cur["カテゴリー"])); nm = st.text_area("材料", value=cur["材料"])
            if st.form_submit_button("更新"):
                df_menu.loc[df_menu["料理名"] == edit_dish, ["料理名", "カテゴリー", "材料"]] = [nn, nc, nm]
                save_to_github(df_menu.to_csv(index=False, encoding="utf-8-sig"), FILE, f"Upd: {nn}", menu_sha)
                st.cache_data.clear(); st.rerun()
    st.divider()
    with st.form("add_menu"):
        an, ac = st.text_input("料理名"), st.selectbox("カテゴリ", ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]); am = st.text_area("材料")
        if st.form_submit_button("追加保存"):
            if an and am:
                save_to_github(pd.concat([df_menu, pd.DataFrame([[an, ac, am]], columns=df_menu.columns)]).to_csv(index=False, encoding="utf-8-sig"), FILE, f"Add: {an}", menu_sha)
                st.cache_data.clear(); st.rerun()
    st.markdown(f'<div style="text-align:right;color:#ddd;font-size:0.6rem;margin-top:50px;">v{VERSION}</div>', unsafe_allow_html=True)
