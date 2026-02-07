# --- 0. バージョン管理情報 ---
VERSION = "1.0.6"  # 履歴の列順（日付・曜日・料理名）と幅を最適化

import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

@st.cache_data(ttl=60)
def get_menu_data():
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(raw))
            df.columns = [c.strip() for c in df.columns]
            return df, r.json()["sha"]
    except: pass
    return None, None

@st.cache_data(ttl=60)
def get_history_data():
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{HIST_FILE}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            return pd.read_csv(io.StringIO(raw)), r.json()["sha"]
        else:
            return pd.DataFrame(columns=["日付", "曜日", "料理名"]), None
    except:
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
    if current_sha:
        data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 2. デザイン定義 ---
st.set_page_config(page_title="献だけ", layout="centered")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span, .stCheckbox {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
        color: #333;
    }
    .main-title { font-family: 'Noto Sans JP', sans-serif !important; font-weight: 100 !important; font-size: 3.2rem; text-align: center; margin: 40px 0; letter-spacing: 0.8rem; }
    .version-label { font-size: 0.7rem; color: #ccc; text-align: right; }
    .shopping-card { background: white; padding: 15px 20px; border-radius: 16px; border: 1px solid #f0f0f0; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }
    .item-row { font-size: 1.1rem; padding: 4px 0; border-bottom: 0.5px solid #f9f9f9; }
    .preview-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin-bottom: 30px; border-radius: 12px; overflow: hidden; border: 1px solid #eee; }
    .preview-table th { background: #fafafa; padding: 10px; border: 1px solid #eee; }
    .preview-table td { padding: 10px; border: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

df_menu, menu_sha = get_menu_data()
df_dict = get_dict_data()
df_hist, hist_sha = get_history_data()

tab_plan, tab_hist, tab_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ メニュー管理"])

day_labels = ["日", "月", "火", "水", "木", "金", "土"]

with tab_plan:
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日）", value=default_sun)

    days_tabs = st.tabs([f"{day_labels[i]}" for i in range(7)])
    cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
    weekly_plan = {}

    for i, day_tab in enumerate(days_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        w_str = day_labels[i]
        with day_tab:
            st.markdown(f"##### {d_str} ({w_str})")
            day_menu = {cat: st.selectbox(cat, ["なし"] + df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=f"s_{i}_{cat}") for cat in cats}
            weekly_plan[d_str] = {"menu": day_menu, "weekday": w_str}

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        st.divider()
        new_history_entries = []
        all_ings_list = []
        rows_html = ""
        
        for d_str, data in weekly_plan.items():
            v = data["menu"]
            w_str = data["weekday"]
            for dish in v.values():
                if dish != "なし":
                    new_history_entries.append({"日付": d_str, "曜日": w_str, "料理名": dish})
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    items = str(ing_raw).replace("、", ",").split(",")
                    all_ings_list.extend([x.strip() for x in items if x.strip()])
            
            m_dish = f"{v.get('主菜1','-')} / {v.get('主菜2','-')}".replace("なし", "-")
            s_dish = f"{v.get('副菜1','-')}, {v.get('副菜2','-')}, {v.get('汁物','-')}".replace("なし", "-")
            rows_html += f'<tr><td>{d_str}({w_str})</td><td>{m_dish}</td><td>{s_dish}</td></tr>'

        if new_history_entries:
            if "曜日" not in df_hist.columns: df_hist["曜日"] = ""
            new_hist_df = pd.concat([df_hist, pd.DataFrame(new_history_entries)], ignore_index=True).drop_duplicates()
            save_to_github(new_hist_df, HIST_FILE, "Update history", hist_sha)
            st.success("履歴を保存しました")

        st.markdown("### 📋 今週の献立チェック")
        st.markdown(f'<table class="preview-table"><tr><th>日付</th><th>主菜</th><th>副菜・汁物</th></tr>{rows_html}</table>', unsafe_allow_html=True)
        st.button("A4印刷する", on_click=lambda: st.write('<script>window.print();</script>', unsafe_allow_html=True))

        if all_ings_list:
            counts = pd.Series(all_ings_list).value_counts()
            result_data = []
            for item, count in counts.items():
                category = "99未分類"
                if df_dict is not None:
                    for _, row in df_dict.iterrows():
                        if row["材料"] in item: category = row["種別"]; break
                result_data.append({"name": f"{item} × {count}" if count > 1 else item, "cat": category})
            
            df_res = pd.DataFrame(result_data).sort_values("cat")
            cards_html = "".join([f'<div class="shopping-card"><div class="category-label">{cat}</div>' + "".join([f'<div class="item-row">□ {row["name"]}</div>' for _, row in group.iterrows()]) + '</div>' for cat, group in df_res.groupby("cat")])
            st.markdown("### 🛒 買い物リスト")
            st.markdown(cards_html, unsafe_allow_html=True)

with tab_hist:
    st.subheader("過去の履歴")
    if not df_hist.empty:
        # 表示用の並び替え
        display_hist = df_hist.sort_values("日付", ascending=False)
        # 列の順番を 日付, 曜日, 料理名 に強制
        display_hist = display_hist[["日付", "曜日", "料理名"]]
        
        st.dataframe(
            display_hist,
            use_container_width=True,
            hide_index=True,
            column_config={
                "日付": st.column_config.TextColumn("日付", width="small"),
                "曜日": st.column_config.TextColumn("曜日", width="small"),
                "料理名": st.column_config.TextColumn("料理名", width="large"),
            }
        )
    else:
        st.info("まだ履歴はありません。")

with tab_manage:
    st.subheader("⚙️ メニュー管理")
    with st.form("add", clear_on_submit=True):
        n = st.text_input("料理名")
        c = st.selectbox("カテゴリー", cats)
        m = st.text_area("材料（「、」区切り）")
        if st.form_submit_button("保存"):
            if n and m:
                new_df = pd.concat([df_menu, pd.DataFrame([[n, c, m]], columns=df_menu.columns)], ignore_index=True)
                if save_to_github(new_df, FILE, f"Add {n}", menu_sha) == 200:
                    st.cache_data.clear()
                    st.rerun()
    st.dataframe(df_menu, use_container_width=True)
    st.markdown(f'<div class="version-label">Version {VERSION}</div>', unsafe_allow_html=True)
