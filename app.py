import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. 接続・認証（安定性確保） ---
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

# --- 2. 視覚設計（重なりを解消し、丸み・細字を貫徹） ---
st.set_page_config(page_title="献だけ", layout="wide")

# CSS: 重なりを防ぐためのパディング調整とデザイン定義
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300&display=swap');
    
    /* 全体のフォント設定（丸みと細字） */
    html, body, [class*="css"], .stMarkdown, p, div, span, label {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }

    /* タイトルエリア：重なりを防ぐために相対位置で余白を確保 */
    .header-container {
        width: 100%;
        padding-top: 20px;
        padding-bottom: 40px;
        text-align: center;
    }
    .main-title {
        font-size: 3rem;
        font-weight: 300;
        color: #333;
    }
</style>
<div class="header-container">
    <div class="main-title">献 だけ</div>
</div>
""", unsafe_allow_html=True)

# --- 3. 献立計画（主菜1, 2 / 副菜1, 2 / 汁物） ---
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

# --- 4. 1週間のメニュー表 ＆ 買い物リスト ---
st.write("")
if st.button("1週間のメニュー表と買い物リストを作成"):
    st.divider()
    res_col1, res_col2 = st.columns([3, 2])
    
    all_ings = []
    with res_col1:
        st.write("📖 １週間のメニュー表")
        table_data = []
        for day, dishes in selected_plan.items():
            row = {"曜日": day}
            row.update(dishes)
            table_data.append(row)
            for d_name in dishes.values():
                if d_name != "選択なし" and not df_master.empty:
                    match = df_master[df_master["料理名"] == d_name]
                    if not match.empty:
                        ing_text = match["材料"].iloc[0]
                        if ing_text:
                            # 買い物リスト用の材料抽出
                            all_ings.extend([x.strip() for x in ing_text.replace("、", "\n").replace(",", "\n").splitlines() if x.strip()])
        
        st.dataframe(pd.DataFrame(table_data), hide_index=True, use_container_width=True)

    with res_col2:
        st.write("🛒 買い物リスト")
        unique_ings = sorted(list(set(all_ings)))
        if unique_ings:
            for item in unique_ings:
                st.checkbox(item, key=f"buy_{item}")
        else:
            st.write("メニューを選んでください。")

# --- 5. 料理の追加・修正 ---
st.write("---")
with st.expander("📝 料理の追加・内容の修正"):
    with st.form("editor", clear_on_submit=True):
        f_c1, f_c2 = st.columns(2)
        with f_c1:
            name = st.text_input("料理名")
        with f_c2:
            cat = st.selectbox("カテゴリー", categories)
        ing = st.text_area("材料（「、」で区切る）")
        
        if st.form_submit_button("保存して反映"):
            if name and spread:
                new_df = df_master[df_master["料理名"] != name]
                add_data = pd.DataFrame([[name, cat, ing]], columns=["料理名", "カテゴリー", "材料"])
                final_df = pd.concat([new_df, add_data], ignore_index=True)
                spread.df_to_sheet(final_df, index=False, replace=True)
                st.success("スプレッドシートを更新しました。")
                st.cache_data.clear()
