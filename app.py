import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials
import json

# --- 1. 接続・認証（ゆっくり、確実に） ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_data(ttl=60)
def get_data():
    try:
        # Secretsをそのまま辞書として読み込む
        # StreamlitはJSONが直接貼られていれば、自動的に辞書として扱ってくれます
        creds_info = dict(st.secrets)
        
        # もし「json_data」という名前の箱の中にデータが入っていた場合の保険
        if "json_data" in creds_info:
            creds_info = json.loads(creds_info["json_data"])

        # 秘密鍵の改行処理（これだけはデジタルのルール上、必須です）
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
            
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        spread = Spread("献だけデータ", creds=creds)
        
        # 画像 image_828fac.png にある通り「シート1」を読み込む
        df = spread.sheet_to_df(sheet="シート1", index=None)
        
        if not df.empty:
            df["カテゴリー"] = df["カテゴリー"].str.strip()
        return spread, df
    except Exception as e:
        # 画面に何が起きているか、ヒントを表示する
        st.error(f"データの読み込みで立ち止まっています: {e}")
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data()

# --- 2. 画面表示と献立作成 ---
st.set_page_config(page_title="献だけ", layout="wide")
st.markdown("<h1 style='text-align: center;'>献だけ</h1>", unsafe_allow_html=True)

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
                    # スプレッドシートのカテゴリーと一致する料理を探す
                    opt = df_master[df_master["カテゴリー"] == c]["料理名"].tolist()
                    day_res[c] = st.selectbox(c, ["未選択"] + opt, key=f"sel_{i}_{j}")
            plan[i] = day_res

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
            st.write("📋 今週の献立")
            st.table(pd.DataFrame(plan).T)
        with c2:
            st.write("🛒 買い物リスト")
            for it in sorted(set(ings)):
                st.checkbox(it, key=f"check_{it}")
else:
    st.info("スプレッドシートを読み込んでいます。しばらくお待ちください...")
