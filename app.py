import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

@st.cache_data(ttl=60)
def get_data():
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
        headers = {"Authorization": f"token {TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            return pd.read_csv(io.StringIO(raw)), r.json()["sha"]
    except: pass
    return None, None

# --- 2. 画面デザイン ---
st.set_page_config(page_title="献だけ", layout="centered")

# CSSでフォントとデザインを統一
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    * { font-family: 'Noto Sans JP', sans-serif !important; font-weight: 300; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("献だけ")

df, sha = get_data()
if df is None:
    st.error("GitHubとの接続に失敗しました。Secretsを確認してください。")
    st.stop()

tab_plan, tab_manage = st.tabs(["🗓 献立作成", "⚙️ メニュー管理"])

with tab_plan:
    # 仕様：日付選択 + 日曜スタート
    today = datetime.now()
    default_sun = today - timedelta(days=(today.weekday() + 1) % 7)
    start_date = st.date_input("開始日（日曜日）", value=default_sun)
    
    st.divider()
    
    # 仕様：曜日ごとのタブで整理
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    days = st.tabs([f"{day_labels[i]} ({(start_date + timedelta(days=i)).strftime('%m/%d')})" for i in range(7)])
    
    cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
    weekly_plan = {}

    for i, day_tab in enumerate(days):
        d_str = (start_date + timedelta(days=i)).strftime("%m/%d")
        with day_tab:
            day_menu = {}
            for cat in cats:
                opts = df[df["カテゴリー"] == cat]["料理名"].tolist()
                day_menu[cat] = st.selectbox(f"{cat}", ["なし"] + opts, key=f"s_{i}_{cat}")
            weekly_plan[d_str] = day_menu

    if st.button("今週の買い物リストを作る", type="primary", use_container_width=True):
        st.subheader("🛒 買い物リスト")
        all_ings = []
        for d_menu in weekly_plan.values():
            for dish in d_menu.values():
                if dish != "なし":
                    m_data = df[df["料理名"] == dish]["材料"].iloc[0]
                    items = str(m_data).replace("、", ",").split(",")
                    all_ings.extend([x.strip() for x in items if x.strip()])
        
        if all_ings:
            # 仕様：材料の重複を集計
            counts = pd.Series(all_ings).value_counts().sort_index()
            cols = st.columns(2)
            for idx, (item, count) in enumerate(counts.items()):
                with cols[idx % 2]:
                    st.checkbox(f"{item} × {count}" if count > 1 else item, key=f"b_{idx}")
        else:
            st.info("料理を選択してください。")

with tab_manage:
    st.subheader("メニューの追加")
    with st.form("add", clear_on_submit=True):
        n = st.text_input("料理名")
        c = st.selectbox("カテゴリー", cats)
        m = st.text_area("材料（「、」で区切る）")
        if st.form_submit_button("GitHubへ保存"):
            if n and m:
                new_df = pd.concat([df, pd.DataFrame([[n, c, m]], columns=df.columns)], ignore_index=True)
                csv_b64 = base64.b64encode(new_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8")).decode("utf-8")
                res = requests.put(f"https://api.github.com/repos/{REPO}/contents/{FILE}", 
                                   headers={"Authorization": f"token {TOKEN}"},
                                   json={"message": "add", "content": csv_b64, "sha": sha})
                if res.status_code == 200:
                    st.success("追加しました！")
                    st.cache_data.clear()
                    st.rerun()

    st.divider()
    st.write("### 現在の登録データ")
    st.dataframe(df, use_container_width=True)
