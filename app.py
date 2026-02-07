# --- 0. バージョン管理情報 ---
VERSION = "1.0.7"  # 印刷ボタンを確実に動作するように修正

import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components  # 追加
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
    /* 印刷時にボタンを隠す */
    @media print {
        .no-print { display: none !important; }
        .stTabs [data-baseweb="tab-list"] { display: none !important; }
    }
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
        st.session_state.confirmed = True
        st.session_state.weekly_plan = weekly_plan # 保存用
        
    if st.session_state.get("confirmed"):
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

        # 履歴保存
        if st.button("この内容で履歴を保存", type="secondary"):
            if new_history_entries:
                if "曜日" not in df_hist.columns: df_hist["曜日"] = ""
                new_hist_df = pd.concat([df_hist, pd.DataFrame(new_history_entries)], ignore_index=True).drop_duplicates()
                save_to_github(new_hist_df, HIST_FILE, "Update history", hist_sha)
                st.success("履歴を保存しました")

        st.markdown("### 📋 今週の献立チェック")
        st.markdown(f'<table class="preview-table"><tr><th>日付</th><th>主菜</th><th>副菜・汁物</th></tr>{rows_html}</table>', unsafe_allow_html=True)
        
        # 確実に動く印刷ボタン（JavaScriptを直接埋め込み）
        components.html(
            """
            <button onclick="window.parent.print()" style="
                width: 100%;
                background-color: #262730;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-family: sans-serif;
            ">A4印刷する（ブラウザの印刷画面が開きます）</button>
            """,
            height=60,
        )

        if all_ings_list:
            counts = pd.Series(all_ings_list).value_counts()
            result_data = []
            for item, count in counts.items():
                category = "99未分類"
                if df_dict is not None:
                    for _, row in df_dict.iterrows():
                        if row["材料"] in item: category = row["種別"]; break
