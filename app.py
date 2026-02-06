import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. スプレッドシート連携（エラーが出ない最小構成） ---
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

# --- 2. 画面全体の設定（細字にするため st.title ではなく st.markdown を使用） ---
st.set_page_config(page_title="献だけ", layout="wide")

# タイトル（見出し2のサイズで、太字を避けてスッキリ表示）
st.markdown("## 🍳 献 だけ")

# --- 3. 献立選択（標準の太さのタブとセレクトボックス） ---
tabs_list = ["月", "火", "水", "木", "金", "土", "日"]
st_tabs = st.tabs(tabs_list)
categories = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

if not df_master.empty:
    for i, tab in enumerate(st_tabs):
        with tab:
            cols = st.columns(5)
            for j, cat in enumerate(categories):
                with cols[j]:
                    # スプレッドシートのカテゴリー列から一致する料理名だけを抽出
                    options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                    # 標準のフォントで表示
                    st.selectbox(cat, ["選択なし"] + options, key=f"{tabs_list[i]}_{cat}")
else:
    st.info("スプレッドシートの読み込みを確認中です。リロードして「カレー」が出るか確認してください。")

# --- 4. 料理の追加（折りたたみ） ---
st.markdown("---")
with st.expander("➕ 新しい料理を追加する"):
    with st.form("add_dish", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("料理名")
        with c2:
            new_cat = st.selectbox("カテゴリー", categories)
        new_ing = st.text_area("材料")
        
        if st.form_submit_button("保存"):
            if new_name and spread:
                new_row = pd.DataFrame([[new_name, new_cat, new_ing]], columns=["料理名", "カテゴリー", "材料"])
                updated_df = pd.concat([df_master, new_row], ignore_index=True)
                spread.df_to_sheet(updated_df, index=False, replace=True)
                st.success("保存完了。ブラウザを更新してください。")

if st.button("献立を確定する"):
    st.balloons()
