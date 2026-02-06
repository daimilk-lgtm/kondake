import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. 接続・認証（PM視点：安定性の確保） ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_data(ttl=60)
def get_data():
    try:
        creds_dict = dict(st.secrets)
        # PEM鍵の正規化：接続エラーを未然に防ぐ
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        spread = Spread("献だけデータ", creds=creds)
        df = spread.sheet_to_df(index=None)
        return spread, df
    except Exception as e:
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data()

# --- 2. デザイナー視点：視覚設計（細字・丸み・中央タイトル） ---
st.set_page_config(page_title="献だけ", layout="wide")

# CSSでフォントとデザインを制御（太字禁止・丸みフォント）
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    h1 {
        text-align: center;
        font-weight: 300 !important;
        font-size: 2.5rem;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_content_html=True)

st.markdown("<h1>献 だけ</h1>", unsafe_content_html=True)

# --- 3. プロデューサー視点：献立計画機能 ---
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
                options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist() if not df_master.empty else []
                val = st.selectbox(cat, ["選択なし"] + options, key=f"{tabs_list[i]}_{cat}")
                day_plan[cat] = val
        selected_plan[tabs_list[i]] = day_plan

# --- 4. 1週間のメニュー表と買い物リスト（主婦層ターゲットの実用的機能） ---
st.write("---")
if st.button("1週間のメニュー表と買い物リストを作成"):
    col_a, col_b = st.columns(2)
    
    all_ingredients = []
    with col_a:
        st.write("🗓 1週間のメニュー表")
        summary_data = []
        for day, dishes in selected_plan.items():
            row = {"曜日": day}
            row.update(dishes)
            summary_data.append(row)
            # 材料集計ロジック
            for dish_name in dishes.values():
                if dish_name != "選択なし":
                    ing = df_master[df_master["料理名"] == dish_name]["材料"].iloc[0]
                    if ing:
                        all_ingredients.extend([x.strip() for x in ing.replace("、", "\n").splitlines() if x.strip()])
        
        st.table(pd.DataFrame(summary_data))

    with col_b:
        st.write("🛒 買い物リスト")
        unique_ingredients = sorted(list(set(all_ingredients)))
        if unique_ingredients:
            for item in unique_ingredients:
                st.checkbox(item, key=f"buy_{item}")
        else:
            st.write("料理を選択するとリストが表示されます。")

# --- 5. 料理の追加・修正（PM視点：データの永続化） ---
st.write("---")
with st.expander("メニューの追加・修正"):
    with st.form("edit_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("料理名（既存名なら修正、新規なら追加）")
        with c2:
            cat = st.selectbox("カテゴリー", categories)
        ing = st.text_area("材料（「、」や改行で区切ってください）")
        
        if st.form_submit_button("スプレッドシートを更新"):
            if name and spread:
                # 既存なら削除して追加（＝修正）、新規ならそのまま追加
                new_df = df_master[df_master["料理名"] != name]
                add_row = pd.DataFrame([[name, cat, ing]], columns=["料理名", "カテゴリー", "材料"])
                final_df = pd.concat([new_df, add_row], ignore_index=True)
                spread.df_to_sheet(final_df, index=False, replace=True)
                st.success(f"「{name}」を保存しました。")
                st.cache_data.clear()
