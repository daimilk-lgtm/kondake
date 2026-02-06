import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- 1. データの読み込み ---
@st.cache_data
def get_clean_df():
    try:
        df = pd.read_csv("menu.csv")
        df["カテゴリー"] = df["カテゴリー"].str.strip()
        return df
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
        return pd.DataFrame()

df_master = get_clean_df()
conn = sqlite3.connect(':memory:', check_same_thread=False)
if not df_master.empty:
    df_master.to_sql('menu_table', conn, index=False, if_exists='replace')

# --- 2. 画面デザイン・仕様メモの反映 ---
# 仕様: タイトルはすべて細字、フォントはNoto Sans JP
st.set_page_config(page_title="献だけ", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300&display=swap');
    html, body, [class*="css"], p, div, select, input, h2, h3 {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .title-wrapper { text-align: center; padding: 1rem 0; }
    .title-text { font-size: 3rem; font-weight: 100; letter-spacing: 0.5em; color: #333; }
    .thin-title { font-weight: 300 !important; font-size: 1.5rem; margin-top: 2rem; }
    .date-text { text-align: right; font-size: 0.8rem; color: #666; }
</style>
<div class="title-wrapper"><div class="title-text">献だけ</div></div>
""", unsafe_allow_html=True)

# 日付の計算
today = datetime.now()
st.markdown(f'<div class="date-text">作成日: {today.strftime("%Y/%m/%d")}</div>', unsafe_allow_html=True)

# --- 3. 献立作成エリア ---
if not df_master.empty:
    # 今週の月曜日の日付を計算
    start_of_week = today - timedelta(days=today.weekday())
    tabs_labels = []
    days_with_date = []
    for i in range(7):
        d = start_of_week + timedelta(days=i)
        day_str = ["月", "火", "水", "木", "金", "土", "日"][i]
        tabs_labels.append(f"{day_str} ({d.strftime('%m/%d')})")
        days_with_date.append(f"{day_str}({d.strftime('%m/%d')})")

    st_tabs = st.tabs(tabs_labels)
    categories = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

    selected_plan = {}
    for i, tab in enumerate(st_tabs):
        with tab:
            cols = st.columns(5)
            day_plan = {}
            for j, cat in enumerate(categories):
                with cols[j]:
                    query = f"SELECT 料理名 FROM menu_table WHERE カテゴリー = '{cat}'"
                    options = pd.read_sql(query, conn)["料理名"].tolist()
                    val = st.selectbox(cat, ["選択なし"] + options, key=f"sel_{i}_{cat}")
                    day_plan[cat] = val
            selected_plan[days_with_date[i]] = day_plan

    st.divider()
    st.subheader("📝 フリーメモ")
    user_memo = st.text_area("メモ", placeholder="追加の買い物など", key="free_memo")

    if st.button("こんだけ作成", type="primary", use_container_width=True):
        st.divider()
        
        # 1. 今週の献立 (縦並び)
        st.markdown('<div class="thin-title">今週の献立</div>', unsafe_allow_html=True)
        df_plan = pd.DataFrame(selected_plan).T
        st.table(df_plan)
        
        # 2. 買い物リスト (縦並び)
        st.markdown('<div class="thin-title">買い物リスト</div>', unsafe_allow_html=True)
        
        if user_memo:
            st.info(f"【追加メモ】\n{user_memo}")
            
        raw_ings = []
        for dishes in selected_plan.values():
            for dish_name in dishes.values():
                if dish_name != "選択なし":
                    match = df_master[df_master["料理名"] == dish_name]
                    if not match.empty:
                        ing = match["材料"].iloc[0]
                        if pd.notna(ing):
                            items = str(ing).replace("、", "\n").replace(",", "\n").splitlines()
                            raw_ings.extend([x.strip() for x in items if x.strip()])

        if raw_ings:
            ing_counts = pd.Series(raw_ings).value_counts().sort_index()
            for name, count in ing_counts.items():
                display_name = f"{name} × {count}" if count > 1 else name
                st.checkbox(display_name, key=f"check_{name}")
        elif not user_memo:
            st.info("メニューを選択してください")
else:
    st.warning("menu.csv を読み込めません。")
