import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# --- 0. バージョン管理情報 ---
VERSION = "1.2.5"  # 主菜2削除 & 定番アイテム改称版

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
            df_h = pd.read_csv(io.StringIO(raw))
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
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

df_menu, menu_sha = get_menu_data()
df_dict = get_dict_data()
df_hist, hist_sha = get_history_data()

if df_menu is None:
    st.error("データの読み込みに失敗しました。")
    st.stop()

# --- 【修正】主菜2を削除 ---
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
            day_menu = {}
            for cat in cats:
                options = df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist()
                day_menu[cat] = st.multiselect(cat, options, key=f"s_{i}_{cat}", placeholder="選択してください")
            
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i]}

    # --- 【修正】「定番アイテム」へ名称変更 ---
    list_options = df_menu[df_menu["カテゴリー"] == "主菜2"]["料理名"].tolist()
    selected_memos = st.multiselect("定番アイテム", list_options, key="list_memo_multi", placeholder="選択してください")

    memo = st.text_area("メモ", placeholder="買い物リストに追加したいもの...")

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        all_ings_list = []
        rows_html = ""
        
        for d_str, data in weekly_plan.items():
            v = data["menu"]
            w_str = data["weekday"]
            
            m_dish = ", ".join(v.get('主菜1', [])) if v.get('主菜1') else "-"
            s1 = ", ".join(v.get('副菜1', [])) if v.get('副菜1') else "-"
            s2 = ", ".join(v.get('副菜2', [])) if v.get('副菜2') else "-"
            sw = ", ".join(v.get('汁物', [])) if v.get('汁物') else "-"
            s_dish = f"{s1}, {s2}, {sw}"
            
            rows_html += f'<tr><td>{d_str}({w_str})</td><td>{m_dish}</td><td>{s_dish}</td></tr>'
            
            for dish_list in v.values():
                for dish in dish_list:
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    items = str(ing_raw).replace("、", ",").split(",")
                    all_ings_list.extend([x.strip() for x in items if x.strip()])

        # 定番アイテムの材料反映
        for selected_dish in selected_memos:
            ing_raw_memo = df_menu[df_menu["料理名"] == selected_dish]["材料"].iloc[0]
            m_items = str(ing_raw_memo).replace("、", ",").split(",")
            all_ings_list.extend([x.strip() for x in m_items if x.strip()])

        if memo:
            memo_items = memo.replace("、", ",").replace("\n", ",").split(",")
            for m_item in memo_items:
                if m_item.strip(): all_ings_list.append(f"{m_item.strip()} (メモ)")

        if all_ings_list:
            counts = pd.Series(all_ings_list).value_counts()
            result_data = []
            for item, count in counts.items():
                category = "99未分類"
                if df_dict is not None:
                    for _, row in df_dict.iterrows():
                        if row["材料"] in item
