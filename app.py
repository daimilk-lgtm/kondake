import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials
import json
import re

# --- 認証とデータ読み込み ---
@st.cache_data(ttl=60)
def get_data():
    try:
        # Secretsから json_data を取得してパース
        if "json_data" not in st.secrets:
            return None, pd.DataFrame()

        info = json.loads(st.secrets["json_data"])
        
        # PEMエラー対策（改行と不要文字の除去）
        if "private_key" in info:
            key = info["private_key"].replace("\\n", "\n")
            info["private_key"] = re.sub(r'[^\x00-\x7F]+', '', key)
            
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        spread = Spread("献だけデータ", creds=creds)
        df = spread.sheet_to_df(sheet="シート1", index=None)
        
        if not df.empty:
            df["カテゴリー"] = df["カテゴリー"].str.strip()
        return spread, df
    except Exception:
        return None, pd.DataFrame()

spread, df_master = get_data()

# --- 画面表示 ---
st.set_page_config(page_title="献だけ", layout="wide")
st.title("献だけ")

if spread is not None and not df_master.empty:
    tabs = st.tabs(["月", "火", "水", "木", "金", "土", "日"])
    cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
    plan = {}

    # 献立選択
    for i, tab in enumerate(tabs):
        with tab:
            cols = st.columns(5)
            day_plan = {}
            for j, c in enumerate(cats):
                with cols[j]:
                    opts = df_master[df_master["カテゴリー"] == c]["料理名"].tolist()
                    day_plan[c] = st.selectbox(c, ["未選択"] + opts, key=f"s_{i}_{j}")
            plan[i] = day_plan

    # 買い物リスト作成
    if st.button("買い物リスト作成", type="primary", use_container_width=True):
        st.divider()
        c1, c2 = st.columns(2)
        
        # リスト集計
        ings = []
        for d in plan.values():
            for m in d.values():
                if m != "未選択":
                    row = df_master[df_master["料理名"] == m]
                    if not row.empty:
                        raw = str(row["材料"].iloc[0])
                        ings.extend([x.strip() for x in raw.replace("、", "\n").splitlines() if x.strip()])
        
        with c1:
            st.write("📋 献立")
            st.table(pd.DataFrame(plan).T)
        with c2:
            st.write("🛒 買い物リスト")
            for it in sorted(set(ings)):
                st.checkbox(it, key=f"buy_{it}")
else:
    st.error("データの読み込みに失敗しました。Secretsの設定を確認してください。")
