import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. 接続設定（エラーを出さない最小・最強構成） ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_data():
    try:
        # Secretsから認証情報を取得
        creds_dict = dict(st.secrets)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        # スプレッドシート「献だけデータ」を読み込み
        spread = Spread("献だけデータ", creds=creds)
        df = spread.sheet_to_df(index=None)
        return spread, df
    except:
        # 接続できない時は空の器だけ用意する
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data()

# --- 2. 画面デザイン（細字・清潔感重視） ---
st.set_page_config(page_title="献だけ", layout="wide")

# タイトルをあえて大きくせず、標準テキストでスマートに
st.write("献 だけ")

# --- 3. 献立選択（標準の細字フォント） ---
tabs_list = ["月", "火", "水", "木", "金", "土", "日"]
st_tabs = st.tabs(tabs_list)
categories = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

for i, tab in enumerate(st_tabs):
    with tab:
        # 5列に分けてスッキリ配置
        cols = st.columns(5)
        for j, cat in enumerate(categories):
            with cols[j]:
                # カレーなど、カテゴリーが一致する料理を取得
                if not df_master.empty:
                    options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                else:
                    options = []
                # 選択ボックス（標準デザイン）
                st.selectbox(cat, ["未選択"] + options, key=f"{tabs_list[i]}_{cat}")

# --- 4. 料理の追加（折りたたみ） ---
st.write("---")
with st.expander("新しい料理を追加"):
    with st.form("add_dish", clear_on_submit=True):
        col_n, col_c = st.columns(2)
        with col_n:
            name = st.text_input("料理名")
        with col_c:
            cat = st.selectbox("カテゴリー", categories)
        ing = st.text_area("材料")
        
        if st.form_submit_button("保存"):
            if name and spread:
                new_row = pd.DataFrame([[name, cat, ing]], columns=["料理名", "カテゴリー", "材料"])
                updated_df = pd.concat([df_master, new_row], ignore_index=True)
                spread.df_to_sheet(updated_df, index=False, replace=True)
                st.success("保存しました。更新してください。")

# 演出ボタン
if st.button("献立を確定"):
    st.balloons()
