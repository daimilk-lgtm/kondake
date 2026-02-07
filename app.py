import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import re

# --- 0. 仕様防衛システム ---
def validate_system_integrity():
    check_results = []
    test_date = datetime(2026, 2, 7) 
    offset = (test_date.weekday() + 1) % 7
    if (test_date - timedelta(days=offset)).weekday() != 6:
        check_results.append("日曜開始ロジック不備")
    return check_results

# --- 1. 設定 ---
VERSION = "test-v1.1.0"
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span { font-family: 'Noto Sans JP', sans-serif !important; font-weight: 300 !important; }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    header[data-testid="stHeader"] { background: transparent !important; color: transparent !important; }
    .shopping-card { background: white; padding: 15px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 10px; color: #333; }
    .category-label { font-size: 0.8rem; color: #999; border-bottom: 1px solid #f9f9f9; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

if validate_system_integrity():
    st.error("システム整合性エラー")
    st.stop()

@st.cache_data(ttl=60)
def get_data(filename):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            return pd.read_csv(io.StringIO(raw)), r.json()["sha"]
    except: pass
    return pd.DataFrame(), None

def save_to_github(df, filename, message, current_sha):
    csv_content = df.to_csv(index=False, encoding="utf-8-sig")
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64, "sha": current_sha}
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 2. メイン ---
st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

df_menu, menu_sha = get_data(FILE)
df_hist, hist_sha = get_data(HIST_FILE)
df_dict, _ = get_data(DICT_FILE)

cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
t_plan, t_hist, t_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ メニュー管理"])

with t_plan:
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    start_date = st.date_input("開始日（日）", value=today - timedelta(days=offset))
    
    weekly_plan = {}
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    d_tabs = st.tabs(day_labels)
    
    for i, tab in enumerate(d_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            day_menu = {c: st.selectbox(c, ["なし"] + df_menu[df_menu["カテゴリー"] == c]["料理名"].tolist(), key=f"v110_{i}_{c}") for c in cats}
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i]}

    memo = st.text_area("メモ")

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        all_ings = []
        new_entries = []
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        for d_str, data in weekly_plan.items():
            for c_type, dish in data["menu"].items():
                if dish != "なし":
                    new_entries.append({"日付": d_str, "曜日": data["weekday"], "料理名": dish, "uid": timestamp})
                    row = df_menu[df_menu["料理名"] == dish]
                    if not row.empty:
                        items = re.split(r'[,、\n]', str(row.iloc[0]["材料"]))
                        all_ings.extend([x.strip() for x in items if x.strip()])
        
        if all_ings:
            st.markdown("---")
            counts = pd.Series(all_ings + ([m.strip() for m in re.split(r'[,、\n]', memo) if m.strip()] if memo else [])).value_counts().reset_index()
            counts.columns = ["name", "count"]
            
            def get_cat(item):
                if df_dict is not None and not df_dict.empty:
                    for _, row in df_dict.iterrows():
                        if row["材料"] in item: return row["種別"]
                return "99未分類"
            
            counts["cat"] = counts["name"].apply(get_cat)
            cards_html = ""
            for cat, group in counts.sort_values("cat").groupby("cat"):
                items_html = "".join([f'<div style="font-size:1.1rem; padding:4px 0;">□ {row["name"]} {"× "+str(row["count"]) if row["count"] > 1 else ""}</div>' for _, row in group.iterrows()])
                cards_html += f'<div class="shopping-card"><div class="category-label">{cat}</div>{items_html}</div>'
            st.markdown(cards_html, unsafe_allow_html=True)
            
            b64_print = base64.b64encode(f"<html><body style='font-family:sans-serif;padding:20px;'><h2>🛒 買い物リスト</h2>{cards_html}</body></html>".encode()).decode()
            components.html(f"""
                <button id="p" style="width:100%; height:45px; background:#262730; color:white; border:none; border-radius:8px; cursor:pointer;">A4印刷</button>
                <script>
                document.getElementById('p').onclick = () => {{
                    var w = window.open();
                    w.document.write(atob('{b64_print}'));
                    w.document.close();
                    setTimeout(() => {{ w.print(); }}, 500);
                }};
                </script>
            """, height=60)

            if new_entries:
                _, l_sha = get_data(HIST_FILE)
                u_hist = pd.concat([df_hist, pd.DataFrame(new_entries)], ignore_index=True).drop_duplicates()
                save_to_github(u_hist, HIST_FILE, f"Update {VERSION}", l_sha)
                st.success("履歴を保存しました")
                st.cache_data.clear()

with t_hist:
    if not df_hist.empty:
        group_cols = ["日付", "曜日"]
        if "uid" in df_hist.columns:
            group_cols.append("uid")
        
        display_df = df_hist.groupby(group_cols, sort=False)["料理名"].apply(lambda x: "、".join(x)).reset_index()
        display_df = display_df.sort_values("日付", ascending=False)
        
        # 料理名列を「折り返し」設定にする
        st.dataframe(
            display_df[["日付", "曜日", "料理名"]],
            column_config={
                "日付": st.column_config.TextColumn("日付", width="small"),
                "曜日": st.column_config.TextColumn("曜日", width="small"),
                "料理名": st.column_config.TextColumn("料理名", width="large"),
            },
            use_container_width=True,
            hide_index=True
        )
        # テーブル全体の行を折り返し表示にするスタイル調整
        st.markdown("""
            <style>
                [data-testid="stTable"] td { white-space: normal !important; }
                div[data-testid="stDataFrame"] div[class*="StyledTableCell"] { white-space: normal !important; }
            </style>
        """, unsafe_allow_html=True)

with t_manage:
    edit_dish = st.selectbox("編集", ["選択してください"] + sorted(df_menu["料理名"].tolist()))
    if edit_dish != "選択してください":
        curr = df_menu[df_menu["料理名"] == edit_dish].iloc[0]
        with st.form("edit_f"):
            n_n = st.text_input("料理名", value=curr["料理名"])
            n_c = st.selectbox("カテゴリー", cats, index=cats.index(curr["カテゴリー"]))
            n_m = st.text_area("材料", value=curr["材料"])
            if st.form_submit_button("保存"):
                df_menu.loc[df_menu["料理名"] == edit_dish, ["料理名", "カテゴリー", "材料"]] = [n_n, n_c, n_m]
                save_to_github(df_menu, FILE, f"Edit {edit_dish}", menu_sha)
                st.rerun()

st.markdown(f'<div style="text-align:right; font-size:0.6rem; color:#ddd;">{VERSION}</div>', unsafe_allow_html=True)
