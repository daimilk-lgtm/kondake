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

# --- 2. デザイン設定 ---
st.set_page_config(page_title="献だけ", layout="wide")
st.title("🍳 献 だけ")

# --- 3. メイン機能：献立選択 ---
tabs_list = ["月", "火", "水", "木", "金", "土", "日"]
st_tabs = st.tabs(tabs_list)
# スプレッドシートのカテゴリー名に合わせて表示
categories = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

for i, tab in enumerate(st_tabs):
    with tab:
        # 横に並べる
        cols = st.columns(len(categories))
        for j, cat in enumerate(categories):
            with cols[j]:
                # そのカテゴリーに合う料理を抽出
                options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                st.selectbox(cat, ["選択なし"] + options, key=f"{tabs_list[i]}_{cat}")

# --- 4. 料理の追加（折りたたみ） ---
st.markdown("---")
with st.expander("➕ 新しい料理をリストに追加する"):
    with st.form("add_dish", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("料理名（例：ハンバーグ）")
        with c2:
            new_cat = st.selectbox("カテゴリー", categories)
        new_ing = st.text_area("材料（メモ）")
        
        if st.form_submit_button("スプレッドシートに保存"):
            if new_name and spread:
                new_row = pd.DataFrame([[new_name, new_cat, new_ing]], columns=["料理名", "カテゴリー", "材料"])
                updated_df = pd.concat([df_master, new_row], ignore_index=True)
                spread.df_to_sheet(updated_df, index=False, replace=True)
                st.success(f"「{new_name}」を保存しました！画面を更新してください。")
            else:
                st.error("料理名を入力してください")

# 演出ボタン
if st.button("今週の献立を確定！"):
    st.balloons()
    st.success("今週も美味しいごはんになりますように！")
