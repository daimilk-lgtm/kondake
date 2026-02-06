import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials
import json
import re

# --- 1. 接続・認証（ゴミ掃除機能付き） ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_data(ttl=60)
def get_data():
    try:
        # Secretsからjson_dataを取り出す
        if "json_data" not in st.secrets:
            st.error("Secretsに 'json_data' が設定されていません。")
            return None, pd.DataFrame()

        # JSONとして読み込む
        info = json.loads(st.secrets["json_data"])
        
        # 【PEMエラー対策】秘密鍵から「目に見えないゴミ文字」を徹底的に除去
        if "private_key" in info:
            key = info["private_key"]
            # 1. バックスラッシュの重複を修正
            key = key.replace("\\n", "\n")
            # 2. 全角スペースや制御文字など、Base64に関係ない文字を掃除
            # (これが InvalidByte の原因)
            key = re.sub(r'[^\x00-\x7F]+', '', key) 
            info["private_key"] = key
            
        creds = Credentials.from_service_account_info(info, scopes=scope)
        spread = Spread("献だけデータ", creds=creds)
        df = spread.sheet_to_df(sheet="シート1", index=None)
        
        if not df.empty:
            df["カテゴリー"] = df["カテゴリー"].str.strip()
        return spread, df
    except Exception as e:
        st.error(f"認証の最終関門でエラー: {e}")
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data()

# --- 2. 画面デザイン ---
st.set_page_config(page_title="献だけ", layout="wide")
st.markdown("<h1 style='text-align: center;'>献だけ</h1>", unsafe_allow_html=True)

# --- 3. 献立作成エリア ---
if not df_master.empty:
    tabs = st.tabs(["月", "火", "水", "木", "金", "土", "日"])
    cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
    plan = {}

    for i, tab in enumerate(tabs):
        with tab:
            cols = st.columns(5)
            day_res = {}
            for j, c in enumerate(cats):
                with cols[j]:
                    opt = df_master[df_master["カテゴリー"] == c]["料理名"].tolist()
                    day_res[c] = st.selectbox(c, ["未選択"] + opt, key=f"s_{i}_{j}")
            plan[i] = day_res

    # --- 4. 買い物リスト生成 ---
    if st.button("買い物リスト作成", type="primary", use_container_width=True):
        ings = []
        for d in plan.values():
            for menu in d.values():
                if menu != "未選択":
                    m_data = df_master[df_master["料理名"] == menu]
                    if not m_data.empty:
                        raw = str(m_data["材料"].iloc[0])
                        ings.extend([x.strip() for x in raw.replace("、", "\n").splitlines() if x.strip()])
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.write("📋 献立表")
            st.table(pd.DataFrame(plan).T)
        with c2:
            st.write("🛒 必要なもの")
            for it in sorted(set(ings)):
                st.checkbox(it, key=f"check_{it}")
else:
    st.warning("スプレッドシートからデータが読み込めませんでした。")
