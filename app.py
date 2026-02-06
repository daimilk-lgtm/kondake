import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials
import json

# --- 1. 接続・認証 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_data(ttl=60)
def get_data():
    try:
        # Secretsから json_data を読み込む
        if "json_data" not in st.secrets:
            return None, pd.DataFrame()

        info = json.loads(st.secrets["json_data"])
        
        # 秘密鍵の改行処理
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
            
        creds = Credentials.from_service_account_info(info, scopes=scope)
        # スプレッドシート名「献だけデータ」
        spread = Spread("献だけデータ", creds=creds)
        # シート1を読み込み
        df = spread.sheet_to_df(sheet="シート1", index=None)
        
        # カテゴリーの余計な空白を削除
        if not df.empty and "カテゴリー" in df.columns:
            df["カテゴリー"] = df["カテゴリー"].str.strip()
            
        return spread, df
    except Exception as e:
        st.error(f"読み込みエラー: {e}")
        return None, pd.DataFrame()

spread, df_master = get_data()

# --- 2. 画面デザイン ---
st.set_page_config(page_title="献だけ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300&display=swap');
    html, body, [class*="css"], p, div, select, input {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .title-wrapper { text-align: center; padding: 2rem 0; }
    .title-text { font-size: 3rem; font-weight: 300; letter-spacing: 0.5em; color: #333; }
</style>
<div class="title-wrapper"><div class="title-text">献だけ</div></div>
""", unsafe_allow_html=True)

# --- 3. 献立作成エリア ---
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
                
                val = st.selectbox(cat, ["選択なし"] + options, key=f"sel_{tabs_list[i]}_{cat}")
                day_plan[cat] = val
        selected_plan[tabs_list[i]] = day_plan

# --- 4. 買い物リスト生成 ---
st.write("")
if st.button("こんだけ作成", type="primary", use_container_width=True):
    st.divider()
    res_col1, res_col2 = st.columns([3, 2])
    
    all_ingredients = []
    
    with res_col1:
        st.subheader("📖 今週の献立")
        display_list = []
        for day, dishes in selected_plan.items():
            row = {"曜日": day}
            row.update(dishes)
            display_list.append(row)
            
            for dish_name in dishes.values():
                if dish_name != "選択なし":
                    match = df_master[df_master["料理名"] == dish_name]
                    if not match.empty:
                        ing_raw = match["材料"].iloc[0]
                        if ing_raw:
                            items = str(ing_raw).replace("、", "\n").replace(",", "\n").splitlines()
                            all_ingredients.extend([x.strip() for x in items if x.strip()])
        
        st.dataframe(pd.DataFrame(display_list), hide_index=True)

    with res_col2:
        st.subheader("🛒 買い物リスト")
        unique_ings = sorted(list(set(all_ingredients)))
        if unique_ings:
            for item in unique_ings:
                st.checkbox(item, key=f"check_{item}")
        else:
            st.info("メニューを選択してください")
