import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. スプレッドシート連携 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_data():
    try:
        creds_dict = dict(st.secrets)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        spread = Spread("献だけデータ", creds=creds)
        df = spread.sheet_to_df(index=None)
        return spread, df
    except:
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data()

# --- 2. 画面全体の設定 ---
st.set_page_config(page_title="献だけ", layout="wide")

# タイトル（ここは大きく）
st.write("### 🍳 献 だけ")

# --- 3. 献立選択（ここから標準の細字になります） ---
tabs_list = ["月", "火", "水", "木", "金", "土", "日"]
st_tabs = st.tabs(tabs_list)
categories = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

for i, tab in enumerate(st_tabs):
    with tab:
        # 5つのカテゴリーを横に並べる
        cols = st.columns(5)
        for j, cat in enumerate(categories):
            with cols[j]:
                # 料理名を探してリストにする
                options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                # 標準の太さのセレクトボックス
                st.selectbox(cat, ["選択なし"] + options, key=f"{tabs_list[i]}_{cat}")

# --- 4. 料理の追加（折りたたみ） ---
st.markdown("---")
with st.expander("➕ 新しい料理をリストに追加する"):
    with st.form("add_dish", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("料理名（例：オムライス）")
        with c2:
            new_cat = st.selectbox("カテゴリー（スプレッドシートの分類）", categories)
        new_ing = st.text_area("材料（覚え書き）")
        
        if st.form_submit_button("スプレッドシートへ保存"):
            if new_name and spread:
                new_row = pd.DataFrame([[new_name, new_cat, new_ing]], columns=["料理名", "カテゴリー", "材料"])
                updated_df = pd.concat([df_master, new_row], ignore_index=True)
                spread.df_to_sheet(updated_df, index=False, replace=True)
                st.success(f"「{new_name}」を保存しました！リロードしてください。")

# 演出
if st.button("今週の献立を確定"):
    st.balloons()
