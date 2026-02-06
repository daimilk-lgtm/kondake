import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. スプレッドシート連携（シンプルに） ---
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

# --- 2. 画面表示（最初にデプロイできた時のスタイル） ---
st.set_page_config(page_title="献だけ", layout="wide")
st.title("献 だけ") # 最初はこのシンプルな左寄せでした

# --- 3. 献立選択機能 ---
tabs = ["月", "火", "水", "木", "金", "土", "日"]
selected_tab = st.tabs(tabs)
categories = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

if not df_master.empty:
    for i, tab in enumerate(selected_tab):
        with tab:
            cols = st.columns(len(categories))
            for j, cat in enumerate(categories):
                with cols[j]:
                    # スプレッドシートの「カテゴリー」列から一致する「料理名」を表示
                    options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                    st.selectbox(cat, ["選択なし"] + options, key=f"{tabs[i]}_{cat}")
else:
    st.info("スプレッドシートのデータを読み込んでいます。")

# --- 4. 料理の追加機能 ---
st.divider()
with st.expander("＋ 新しい料理を登録する"):
    with st.form("add_dish", clear_on_submit=True):
        new_name = st.text_input("料理名")
        new_cat = st.selectbox("カテゴリー", categories)
        new_ingredients = st.text_area("材料メモ")
        if st.form_submit_button("保存"):
            if new_name and spread:
                new_row = pd.DataFrame([[new_name, new_cat, new_ingredients]], columns=["料理名", "カテゴリー", "材料"])
                updated_df = pd.concat([df_master, new_row], ignore_index=True)
                spread.df_to_sheet(updated_df, index=False, replace=True)
                st.success(f"「{new_name}」を保存しました。更新してください。")

# 演出（風船などは一切削除しました）
if st.button("献立確定"):
    st.success("今週の献立を確定しました。")
