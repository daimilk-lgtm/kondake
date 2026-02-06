import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials
import time

# --- 1. 接続・認証（超シンプル＆待機モード） ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_data_manual():
    try:
        # Secretsから直接1つずつ取り出す（一番エラーが起きにくい）
        p_key = st.secrets["PRIVATE_KEY"].replace("\\n", "\n")
        c_email = st.secrets["CLIENT_EMAIL"]
        
        creds_dict = {
            "type": "service_account",
            "private_key": p_key,
            "client_email": c_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        
        # 「高速すぎてダメ」対策：少しだけ待つ
        time.sleep(1)
        
        spread = Spread("献だけデータ", creds=creds)
        # キャッシュを介さず直接シート1を読む
        df = spread.sheet_to_df(sheet="シート1", index=None)
        
        if not df.empty:
            df["カテゴリー"] = df["カテゴリー"].str.strip()
        return spread, df
    except Exception as e:
        st.error(f"読み込み失敗。設定を確認してください: {e}")
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

# あえて st.cache は使わず、毎回読みに行く（「高速」の弊害を防ぐため）
spread, df_master = get_data_manual()

# --- 2. 画面表示 ---
st.set_page_config(page_title="献だけ", layout="wide")
st.title("献だけ")

# 曜日ごとのタブ
tabs = st.tabs(["月", "火", "水", "木", "金", "土", "日"])
cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
plan = {}

# メニュー選択
for i, tab in enumerate(tabs):
    with tab:
        cols = st.columns(5)
        day_res = {}
        for j, c in enumerate(cats):
            with cols[j]:
                opt = df_master[df_master["カテゴリー"] == c]["料理名"].tolist() if not df_master.empty else []
                day_res[c] = st.selectbox(c, ["未選択"] + opt, key=f"key_{i}_{j}")
        plan[i] = day_res

# 買い物リスト
if st.button("買い物リスト作成", use_container_width=True):
    ings = []
    for d in plan.values():
        for m in d.values():
            if m != "未選択":
                match = df_master[df_master["料理名"] == m]
                if not match.empty:
                    raw = str(match["材料"].iloc[0])
                    ings.extend([x.strip() for x in raw.replace("、", "\n").splitlines() if x.strip()])
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write("📋 献立表")
        st.table(pd.DataFrame(plan).T)
    with c2:
        st.write("🛒 買い物リスト")
        for it in sorted(set(ings)):
            st.checkbox(it, key=f"it_{it}")
