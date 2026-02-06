import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. スプレッドシート連携の設定 ---
# GoogleのAPIを利用するための許可証（スコープ）
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def get_data_from_sheets():
    # StreamlitのSecrets（さっき保存した青いボタンのところ）から鍵を読み込む
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        
        # スプレッドシート名「献だけデータ」を開く
        spread = Spread("献だけデータ", creds=creds)
        # シートのデータを読み込んで表（DataFrame）にする
        df = spread.sheet_to_df(index=None)
        return spread, df
    except Exception as e:
        # 万が一エラーが出た場合は画面に表示する
        st.error(f"スプレッドシートとの接続に失敗しました: {e}")
        # 空の表を返してアプリが止まらないようにする
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

# データを実際に取得
spread, df_master = get_data_from_sheets()

# --- 2. 画面のデザイン ---
st.set_page_config(page_title="献だけ", layout="wide")
st.title("献 だけ")
st.write("スプレッドシートから献立を読み込んでいます...")

# --- 3. メイン機能：曜日ごとの献立選択 ---
tabs = ["月", "火", "水", "木", "金", "土", "日"]
selected_tab = st.tabs(tabs)
categories = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

for i, tab in enumerate(selected_tab):
    with tab:
        cols = st.columns(len(categories))
        for j, cat in enumerate(categories):
            with cols[j]:
                # スプレッドシートの「カテゴリー」列と一致する料理だけをリストアップ
                options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                st.selectbox(cat, ["なし"] + options, key=f"{tabs[i]}_{cat}")

# --- 4. 料理の追加機能（スプレッドシートへ保存） ---
st.divider()
with st.expander("＋ 新しい料理をスプレッドシートに登録する"):
    with st.form("add_dish"):
        new_name = st.text_input("料理名（例：ハンバーグ）")
        new_cat = st.selectbox("カテゴリー", categories)
        new_ingredients = st.text_area("材料やメモ")
        submit = st.form_submit_button("スプレッドシートに保存")
        
        if submit and new_name:
            if spread is not None:
                # 新しい料理を一行追加
                new_row = pd.DataFrame([[new_name, new_cat, new_ingredients]], columns=["料理名", "カテゴリー", "材料"])
                updated_df = pd.concat([df_master, new_row], ignore_index=True)
                
                # スプレッドシートに書き込み（上書き保存）
                spread.df_to_sheet(updated_df, index=False, replace=True)
                st.success(f"「{new_name}」をスプレッドシートに書き込みました！ブラウザを更新して反映させてください。")
            else:
                st.error("スプレッドシートにアクセスできません。")

if st.button("今週の献立を確定（演出
