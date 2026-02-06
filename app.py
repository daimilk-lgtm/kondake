import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. 接続設定（安定性重視） ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_data(ttl=60)
def get_data():
    try:
        creds_dict = dict(st.secrets)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        spread = Spread("献だけデータ", creds=creds)
        df = spread.sheet_to_df(index=None)
        return spread, df
    except:
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data()

# --- 2. UI設計（仕様書準拠：中央タイトル・太字NG） ---
st.set_page_config(page_title="献だけ", layout="wide")

# タイトルを中央寄せにするための最小限の安全な記述
st.markdown("<h1 style='text-align: center; font-weight: 300;'>献 だけ</h1>", unsafe_content_html=True)

# --- 3. 献立計画（仕様書：主菜2・副菜2・汁物の5項目） ---
tabs_list = ["月", "火", "水", "木", "金", "土", "日"]
st_tabs = st.tabs(tabs_list)
categories = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

selected_plan = {}

for i, tab in enumerate(st_tabs):
    with tab:
        cols = st.columns(5)
        day_plan = {}
        for j, cat in enumerate(categories):
            with cols[j]:
                options = []
                if not df_master.empty:
                    options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                
                # ユーザーが混乱しないよう、標準の細字セレクトボックス
                val = st.selectbox(cat, ["選択なし"] + options, key=f"{tabs_list[i]}_{cat}")
                day_plan[cat] = val
        selected_plan[tabs_list[i]] = day_plan

# --- 4. 買い物リストとメニュー表（主婦層向け必須機能） ---
st.write("---")
if st.button("1週間のメニュー表と買い物リストを作成"):
    col_a, col_b = st.columns(2)
    
    all_ingredients = []
    with col_a:
        st.write("🗓 メニュー表")
        summary = []
        for day, dishes in selected_plan.items():
            row = {"曜日": day}
            row.update(dishes)
            summary.append(row)
            # 材料データの紐付け
            for dish in dishes.values():
                if dish != "選択なし" and not df_master.empty:
                    match = df_master[df_master["料理名"] == dish]
                    if not match.empty:
                        ing = match["材料"].iloc[0]
                        if ing:
                            # 区切り文字を統一してリスト化
                            all_ingredients.extend([x.strip() for x in ing.replace("、", "\n").replace(",", "\n").splitlines() if x.strip()])
        
        st.dataframe(pd.DataFrame(summary), hide_index=True)

    with col_b:
        st.write("🛒 買い物リスト")
        unique_ings = sorted(list(set(all_ingredients)))
        if unique_ings:
            for item in unique_ings:
                st.checkbox(item, key=f"list_{item}")
        else:
            st.write("料理を選ぶとリストが出ます")

# --- 5. 追加・修正機能 ---
st.write("---")
with st.expander("メニューの追加・修正"):
    with st.form("edit", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("料理名")
        with c2:
            cat = st.selectbox("カテゴリー", categories)
        ing = st.text_area("材料（「、」で区切る）")
        
        if st.form_submit_button("保存"):
            if name and spread:
                # 修正（既存削除）→ 追加のロジック
                new_df = df_master[df_master["料理名"] != name]
                add_row = pd.DataFrame([[name, cat, ing]], columns=["料理名", "カテゴリー", "材料"])
                final_df = pd.concat([new_df, add_row], ignore_index=True)
                spread.df_to_sheet(final_df, index=False, replace=True)
                st.success("更新しました")
                st.cache_data.clear()
