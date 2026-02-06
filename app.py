import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. 接続設定 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_data():
    try:
        creds_dict = dict(st.secrets)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        # スプレッドシート名「献だけデータ」を開く
        spread = Spread("献だけデータ", creds=creds)
        # 1枚目のシートをデータフレームとして読み込む
        df = spread.sheet_to_df(index=None)
        return spread, df
    except Exception as e:
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data()

# --- 2. 画面デザイン（標準の細字設定） ---
st.set_page_config(page_title="献だけ", layout="wide")

# タイトル（太字にならないよう、標準のテキストサイズで表示）
st.markdown("### 🍳 献 だけ")

# --- 3. メイン：献立選択タブ ---
tabs_list = ["月", "火", "水", "木", "金", "土", "日"]
st_tabs = st.tabs(tabs_list)
categories = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

# スプレッドシートに「カレー」などのデータがある場合
if not df_master.empty:
    for i, tab in enumerate(st_tabs):
        with tab:
            # カテゴリー（主菜1など）を横に5つ並べる
            cols = st.columns(len(categories))
            for j, cat in enumerate(categories):
                with cols[j]:
                    # スプレッドシートの「カテゴリー」列が一致する「料理名」を取得
                    options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                    # 標準のフォントで選択肢を表示
                    st.selectbox(cat, ["未選択"] + options, key=f"{tabs_list[i]}_{cat}")
else:
    # データが読み込めていない時の表示
    st.warning("スプレッドシートにデータが見つかりません。1行目に「料理名」「カテゴリー」「材料」という見出しがあるか確認してください。")

# --- 4. 料理の追加（折りたたみ） ---
st.markdown("---")
with st.expander("➕ 新しい料理をリストに追加する"):
    with st.form("add_dish", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("料理名（例：ハンバーグ）")
        with c2:
            cat = st.selectbox("カテゴリー", categories)
        ing = st.text_area("材料メモ")
        
        if st.form_submit_button("保存"):
            if name and spread:
                # 新しい行を作ってスプレッドシートに送る
                new_row = pd.DataFrame([[name, cat, ing]], columns=["料理名", "カテゴリー", "材料"])
                updated_df = pd.concat([df_master, new_row], ignore_index=True)
                spread.df_to_sheet(updated_df, index=False, replace=True)
                st.success(f"「{name}」を保存しました。リロードして確認してください。")

if st.button("今週の献立を確定"):
    st.balloons()
