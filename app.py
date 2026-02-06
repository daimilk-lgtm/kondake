import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials
import json

# --- 1. スプレッドシート連携の設定 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_data_from_sheets():
    try:
        s = st.secrets
        # Secretsを辞書に変換
        creds_dict = dict(s["gcp_service_account"] if "gcp_service_account" in s else s)
        
        # --- 鍵の超強力掃除 ---
        if "private_key" in creds_dict:
            pk = creds_dict["private_key"]
            # 1. まず「実際の改行」を \n という文字に統一
            pk = pk.replace("\n", "\\n")
            # 2. BEGIN/END行が重複したり崩れたりするのを防ぐため一旦全部繋げる
            pk = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").replace("\\n", "")
            # 3. 64文字ごとに改行（\n）を入れる正式なPEM形式に再構築
            body = "\n".join([pk[i:i+64] for i in range(0, len(pk), 64)])
            creds_dict["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{body}\n-----END PRIVATE KEY-----\n"

        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        spread = Spread("献だけデータ", creds=creds)
        df = spread.sheet_to_df(index=None)
        return spread, df
    except Exception as e:
        # エラーが起きても、アプリを止めずに画面に理由を出す
        st.error(f"接続エラー: {e}")
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data_from_sheets()

# --- 2. 画面表示 ---
st.set_page_config(page_title="献だけ", layout="wide")
st.title("献 だけ")

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
                    # スプレッドシートの「カテゴリー」列と一致する料理をリスト化
                    options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                    st.selectbox(cat, ["なし"] + options, key=f"{tabs[i]}_{cat}")
else:
    st.info("スプレッドシートのデータ（カレーなど）を探しています。出ない場合はリロードしてください。")

# --- 4. 料理の追加機能 ---
st.divider()
with st.expander("＋ 新しい料理を登録する"):
    with st.form("add_dish"):
        new_name = st.text_input("料理名")
        new_cat = st.selectbox("カテゴリー", categories)
        new_ingredients = st.text_area("材料メモ")
        if st.form_submit_button("保存"):
            if new_name and spread is not None:
                new_row = pd.DataFrame([[new_name, new_cat, new_ingredients]], columns=["料理名", "カテゴリー", "材料"])
                updated_df = pd.concat([df_master, new_row], ignore_index=True)
                spread.df_to_sheet(updated_df, index=False, replace=True)
                st.success("保存しました！リロードして反映させてください。")

if st.button("献立確定"):
    st.balloons()
