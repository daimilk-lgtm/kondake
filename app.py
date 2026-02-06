import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. スプレッドシート連携（エラーを出さない最小・最強構成） ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_data(ttl=60) # 1分間データをキャッシュして動作を軽くする
def get_data():
    try:
        creds_dict = dict(st.secrets)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        # スプレッドシート「献だけデータ」を読み込み
        spread = Spread("献だけデータ", creds=creds)
        df = spread.sheet_to_df(index=None)
        return spread, df
    except:
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data()

# --- 2. 画面デザイン ---
st.set_page_config(page_title="献だけ", layout="wide")

# 【修正】タイトルを中央揃えにし、フォントを大きく表示
st.markdown("<h1 style='text-align: center;'>🍳 献 だけ</h1>", unsafe_content_html=True)

# --- 3. 献立選択（タブと中身は標準の細字） ---
tabs_list = ["月", "火", "水", "木", "金", "土", "日"]
st_tabs = st.tabs(tabs_list)
categories = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

for i, tab in enumerate(st_tabs):
    with tab:
        # カテゴリーを横に並べる
        cols = st.columns(5)
        for j, cat in enumerate(categories):
            with cols[j]:
                # スプレッドシートから該当カテゴリーの料理を抽出
                if not df_master.empty:
                    options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                else:
                    options = []
                # 標準のフォントで選択
                st.selectbox(cat, ["選択なし"] + options, key=f"{tabs_list[i]}_{cat}")

# --- 4. 料理の追加（折りたたみ） ---
st.write("---")
with st.expander("➕ 新しい料理をリストに追加する"):
    with st.form("add_dish", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("料理名")
        with c2:
            cat = st.selectbox("カテゴリー", categories)
        ing = st.text_area("材料（メモ）")
        
        if st.form_submit_button("スプレッドシートに保存"):
            if name and spread:
                new_row = pd.DataFrame([[name, cat, ing]], columns=["料理名", "カテゴリー", "材料"])
                updated_df = pd.concat([df_master, new_row], ignore_index=True)
                spread.df_to_sheet(updated_df, index=False, replace=True)
                st.success(f"「{name}」を保存しました。更新してください。")
                st.cache_data.clear() # キャッシュを消して最新にする

# 演出
if st.button("今週の献立を確定！"):
    st.balloons()
