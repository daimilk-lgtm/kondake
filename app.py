import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. スプレッドシート連携の設定 ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def get_data_from_sheets():
    try:
        s = st.secrets
        creds_dict = s["gcp_service_account"] if "gcp_service_account" in s else dict(s)
        
        # 【重要】鍵の中にある「変な改行」や「スペース」を自動でお掃除する
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()

        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        # スプレッドシート「献だけデータ」を開く
        spread = Spread("献だけデータ", creds=creds)
        df = spread.sheet_to_df(index=None)
        return spread, df
    except Exception as e:
        # エラーが出ても詳細を表示して原因を突き止める
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
                    options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                    st.selectbox(cat, ["なし"] + options, key=f"{tabs[i]}_{cat}")
else:
    # 接続はできたけどシートが空の場合
    st.info("スプレッドシートとの接続は成功しましたが、データがまだ空です。下のフォームから料理を追加してください。")

# --- 4. 料理の追加機能 ---
st.divider()
with st.expander("＋ 新しい料理を登録する"):
    with st.form("add_dish"):
        new_name = st.text_input("料理名")
        new_cat = st.selectbox("カテゴリー", categories)
        new_ingredients = st.text_area("材料メモ")
        submit = st.form_submit_button("保存")
        
        if submit and new_name:
            if spread is not None:
                new_row = pd.DataFrame([[new_name, new_cat, new_ingredients]], columns=["料理名", "カテゴリー", "材料"])
                updated_df = pd.concat([df_master, new_row], ignore_index=True)
                spread.df_to_sheet(updated_df, index=False, replace=True)
                st.success(f"保存しました！ページを更新して反映させてください。")

if st.button("献立確定"):
    st.balloons()
