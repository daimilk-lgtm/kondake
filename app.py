import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials
import json

# --- 1. 認証 (何が貼られても動くように徹底ガード) ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_data(ttl=60)
def get_data():
    try:
        s_dict = dict(st.secrets)
        # JSON丸ごと貼り付けでも、項目バラバラでも対応
        info = s_dict.get("json_data", s_dict)
        if isinstance(info, str):
            info = json.loads(info)
        
        # 鍵の改行をプログラム側で強制修正
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
            
        creds = Credentials.from_service_account_info(info, scopes=scope)
        spread = Spread("献だけデータ", creds=creds)
        # シート名は「シート1」で固定
        df = spread.sheet_to_df(sheet="シート1", index=None)
        
        if not df.empty:
            df["カテゴリー"] = df["カテゴリー"].str.strip()
        return spread, df
    except Exception as e:
        st.error(f"エラー発生。私の指示が不適切でした: {e}")
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data()

# --- 2. 画面表示 ---
st.set_page_config(page_title="献だけ", layout="wide")
st.title("献だけ")

# --- 3. 献立選択 ---
tabs = st.tabs(["月", "火", "水", "木", "金", "土", "日"])
cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
plan = {}

for i, tab in enumerate(tabs):
    with tab:
        cols = st.columns(5)
        day_res = {}
        for j, c in enumerate(cats):
            with cols[j]:
                opt = []
                if not df_master.empty:
                    opt = df_master[df_master["カテゴリー"] == c]["料理名"].tolist()
                day_res[c] = st.selectbox(c, ["未選択"] + opt, key=f"{i}{j}")
        plan[i] = day_res

# --- 4. 買い物リスト ---
if st.button("作成", use_container_width=True):
    ings = []
    for d in plan.values():
        for menu in d.values():
            if menu != "未選択":
                m_data = df_master[df_master["料理名"] == menu]
                if not m_data.empty:
                    raw = str(m_data["材料"].iloc[0])
                    ings.extend([x.strip() for x in raw.replace("、", "\n").splitlines() if x.strip()])
    
    c1, c2 = st.columns(2)
    with c1:
        st.write("📋 今週の献立")
        st.table(pd.DataFrame(plan).T)
    with c2:
        st.write("🛒 買い物")
        for it in sorted(set(ings)):
            st.checkbox(it, key=f"shop_{it}")
