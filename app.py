import streamlit as st
import pandas as pd
import sqlite3

# --- 1. データの読み込み (キャッシュはデータのみにする) ---
@st.cache_data
def get_clean_df():
    try:
        # menu.csv を読み込む
        df = pd.read_csv("menu.csv")
        df["カテゴリー"] = df["カテゴリー"].str.strip()
        return df
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
        return pd.DataFrame()

df_master = get_clean_df()

# SQLiteの接続を確立（キャッシュの外で行う）
conn = sqlite3.connect(':memory:', check_same_thread=False)
if not df_master.empty:
    df_master.to_sql('menu_table', conn, index=False, if_exists='replace')

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
if not df_master.empty:
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
                    # カテゴリーに合う料理を抽出
                    query = f"SELECT 料理名 FROM menu_table WHERE カテゴリー = '{cat}'"
                    options = pd.read_sql(query, conn)["料理名"].tolist()
                    
                    val = st.selectbox(cat, ["選択なし"] + options, key=f"sel_{tabs_list[i]}_{cat}")
                    day_plan[cat] = val
            selected_plan[tabs_list[i]] = day_plan

    # --- 4. 買い物リスト生成 ---
    if st.button("こんだけ作成", type="primary", use_container_width=True):
        st.divider()
        col1, col2 = st.columns([3, 2])
        
        all_ingredients = []
        with col1:
            st.subheader("📖 今週の献立")
            st.table(pd.DataFrame(selected_plan).T)
            
            for dishes in selected_plan.values():
                for dish_name in dishes.values():
                    if dish_name != "選択なし":
                        match = df_master[df_master["料理名"] == dish_name]
                        if not match.empty:
                            ing = match["材料"].iloc[0]
                            if pd.notna(ing):
                                items = str(ing).replace("、", "\n").replace(",", "\n").splitlines()
                                all_ingredients.extend([x.strip() for x in items if x.strip()])

        with col2:
            st.subheader("🛒 買い物リスト")
            unique_ings = sorted(list(set(all_ingredients)))
            if unique_ings:
                for item in unique_ings:
                    st.checkbox(item, key=f"check_{item}")
            else:
                st.info("メニューを選択してください")
else:
    st.warning("menu.csv の内容が読み込めません。")
