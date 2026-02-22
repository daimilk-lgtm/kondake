import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta

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
# - [2026/02/22] 読み込み失敗時、エラーを握りつぶさずStatus Codeやレスポンス詳細を表示。
# ==============================================================================

VERSION = "1.3.4"

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

def get_menu_data():
    """メニューデータを取得。失敗時はエラーの詳細を画面に出力する。"""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(raw))
            return df, r.json()["sha"]
        else:
            st.error(f"GitHub読み込みエラー (Status: {r.status_code})")
            st.info(f"アクセス先: {REPO}/{FILE}")
            st.write("レスポンス内容:", r.text)
            return None, None
    except Exception as e:
        st.error(f"通信エラーが発生しました: {e}")
        return None, None

@st.cache_data(ttl=60)
def get_history_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{HIST_FILE}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df_h = pd.read_csv(io.StringIO(raw))
            if "uid" in df_h.columns: df_h = df_h.drop(columns=["uid"])
            return df_h, r.json()["sha"]
    except: pass
    return pd.DataFrame(columns=["日付", "曜日", "料理名"]), None

@st.cache_data(ttl=60)
def get_dict_data():
    try:
        url = f"https://raw.githubusercontent.com/{REPO}/main/{DICT_FILE}"
        return pd.read_csv(url)
    except: return None

def save_to_github(df, filename, message, current_sha=None):
    csv_content = df.to_csv(index=False, encoding="utf-8-sig")
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
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
    .item-row { font-size: 1.1rem; padding: 4px 0; border-bottom: 0.5px solid #f9f9f9; }
    .preview-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin-top: 10px; margin-bottom: 20px; }
    .preview-table th, .preview-table td { border: 1px solid #eee; padding: 8px; text-align: left; }
    .preview-table th { background-color: #fcfcfc; font-weight: 400; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

# データの取得実行
df_menu, menu_sha = get_menu_data()
df_dict = get_dict_data()
df_hist, hist_sha = get_history_data()

if df_menu is None:
    st.stop() 

cats = ["主菜1", "副菜1", "副菜2", "汁物"]
tab_plan, tab_hist, tab_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ メニュー管理"])

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
            day_menu = {cat: st.multiselect(cat, df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=f"s_{i}_{cat}", placeholder="選択...") for cat in cats}
            day_memo = st.text_input("この日のメモ", key=f"memo_{i}", placeholder="買い足すものなど...")
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i], "memo": day_memo}

    list_memo_options = df_menu[df_menu["カテゴリー"] == "主菜2"]["料理名"].tolist()
    selected_memos = st.multiselect("定番アイテム", list_memo_options, key="list_memo_multi", placeholder="選択...")

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        all_ings_list = []
        rows_html = ""
        new_history_entries = []
        
        for d_str, data in weekly_plan.items():
            v = data["menu"]
            w_str = data["weekday"]
            d_memo = data["memo"]
            
            m1 = ", ".join(v.get('主菜1', [])) if v.get('主菜1') else "-"
            s1 = ", ".join(v.get('副菜1', [])) if v.get('副菜1') else "-"
            s2 = ", ".join(v.get('副菜2', [])) if v.get('副菜2') else "-"
            sw = ", ".join(v.get('汁物', [])) if v.get('汁物') else "-"
            s_dish = f"{s1}, {s2}, {sw}"
            
            rows_html += f'<tr><td>{d_str}({w_str})</td><td>{m1}</td><td>{s_dish}</td></tr>'
            
            for dish_list in v.values():
                for dish in dish_list:
                    new_history_entries.append({"日付": d_str, "曜日": w_str, "料理名": dish})
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    all_ings_list.extend([x.strip() for x in str(ing_raw).replace("、", ",").split(",") if x.strip()])
            
            if d_memo:
                all_ings_list.extend([x.strip() + " (メモ)" for x in d_memo.replace("、", ",").split(",") if x.strip()])

        for selected_dish in selected_memos:
            ing_raw_memo = df_menu[df_menu["料理名"] == selected_dish]["材料"].iloc[0]
            all_ings_list.extend([x.strip() for x in str(ing_raw_memo).replace("、", ",").split(",") if x.strip()])

        if new_history_entries:
            df_combined_h = pd.concat([df_hist, pd.DataFrame(new_history_entries)], ignore_index=True).drop_duplicates()
            save_to_github(df_combined_h, HIST_FILE, "Update history", hist_sha)
            st.toast("履歴を保存しました")

        st.markdown("### 🗓 確定した献立")
        st.markdown(f'<table class="preview-table"><tr><th>日付</th><th>主菜</th><th>副菜・汁物</th></tr>{rows_html}</table>', unsafe_allow_html=True)

        if all_ings_list:
            counts = pd.Series(all_ings_list).value_counts()
            result_data = []
            for item, count in counts.items():
                category = "99未分類"
                if df_dict is not None:
                    for _, row in df_dict.iterrows():
                        if str(row["材料"]) in str(item): category = row["種別"]; break
                result_data.append({"name": f"{item} × {count}" if count > 1 else item, "cat": category})
            
            df_res = pd.DataFrame(result_data).sort_values("cat")
            cards_html = "".join([f'<div class="shopping-card"><div class="category-label">{cat}</div>' + "".join([f'<div class="item-row">□ {row["name"]}</div>' for _, row in group.iterrows()]) + '</div>' for cat, group in df_res.groupby("cat")])
            st.markdown("### 🛒 買い物リスト")
            st.markdown(cards_html, unsafe_allow_html=True)

            raw_html = f"<html><body style='font-family:sans-serif;padding:20px;'><h2>🗓 献立</h2><table style='width:100%;border-collapse:collapse;margin-bottom:20px;' border='1'><tr><th>日付</th><th>主菜</th><th>副菜・汁物</th></tr>{rows_html}</table><h2>🛒 買い物リスト</h2>{cards_html}</body></html>"
            b64_html = base64.b64encode(raw_html.encode('utf-8')).decode('utf-8')
            components.html(f"""
                <div style="margin-top:20px;"><button id="pbtn" style="width:100%;background-color:#262730;color:white;padding:12px;border:none;border-radius:8px;cursor:pointer;font-size:1rem;">A4印刷する</button></div>
                <script>
                document.getElementById('pbtn').onclick = function() {{
                    var html = atob('{b64_html}');
                    var w = window.open('', '_blank');
                    w.document.open(); w.document.write(decodeURIComponent(escape(html))); w.document.close();
                    setTimeout(function() {{ w.focus(); w.print(); }}, 500);
                }};
                </script>
            """, height=80)

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
                save_to_github(df_hist, HIST_FILE, f"Delete history {target_date}", hist_sha)
                st.cache_data.clear()
                st.rerun()
        with col2:
            new_hist_name = st.text_input("料理名を修正", value=df_hist_display.iloc[selected_hist_idx]['料理名'])
            if st.button("料理名を修正して保存", type="primary", use_container_width=True):
                target_date = df_hist_display.iloc[selected_hist_idx]['日付']
                target_name = df_hist_display.iloc[selected_hist_idx]['料理名']
                df_hist.loc[(df_hist['日付'] == target_date) & (df_hist['料理名'] == target_name), '料理名'] = new_hist_name
                save_to_github(df_hist, HIST_FILE, f"Edit history {target_date}", hist_sha)
                st.cache_data.clear()
                st.rerun()
        
        st.divider()
        st.dataframe(df_hist_display, use_container_width=True, hide_index=True)

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
                save_to_github(df_menu, FILE, f"Update {edit_dish}", menu_sha)
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
                save_to_github(new_df, FILE, f"Add {n}", menu_sha)
                st.cache_data.clear()
                st.rerun()

    st.markdown(f'<div style="text-align: right; color: #ddd; font-size: 0.6rem; margin-top: 50px;">Version {VERSION}</div>', unsafe_allow_html=True)
