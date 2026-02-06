import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. スプレッドシート連携 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_data():
    try:
        # Secretsをそのまま読み込む
        creds_dict = dict(st.secrets)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        # スプレッドシート名「献だけデータ」を開く
        spread = Spread("献だけデータ", creds=creds)
        df = spread.sheet_to_df(index=None)
        return spread, df
    except Exception as e:
        # エラーは無視して進む（画面を汚さないため）
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data()

# --- 2. 画面表示 ---
st.set_page_config(page_title="献だけ", layout="wide")
st.title("献 だけ")

# --- 3. 献立選択 ---
tabs = ["月", "火", "水", "木", "金", "土", "日"]
selected_tabs = st.tabs(tabs)
categories = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

if not df_master.empty:
    for i, tab in enumerate(selected_tabs):
        with tab:
            cols = st.columns(len(categories))
            for j, cat in enumerate(categories):
                with cols[j]:
                    options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                    st.selectbox(cat, ["なし"] + options, key=f"{tabs[i]}_{cat}")
else:
    st.info("スプレッドシート「献だけデータ」から料理を探しています。")

# --- 4. 料理登録 ---
st.divider()
with st.expander("＋ 新しい料理を登録する"):
    with st.form("add_dish"):
        new_name = st.text_input("料理名")
        new_cat = st.selectbox("カテゴリー", categories)
        new_ing = st.text_area("材料")
        if st.form_submit_button("保存") and new_name and spread:
            new_row = pd.DataFrame([[new_name, new_cat, new_ing]], columns=["料理名", "カテゴリー", "材料"])
            updated_df = pd.concat([df_master, new_row], ignore_index=True)
            spread.df_to_sheet(updated_df, index=False, replace=True)
            st.success("保存しました！リロードしてください。")

if st.button("献立確定"):
    st.balloons()
