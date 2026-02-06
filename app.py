import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. 接続・認証（変更なし） ---
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

# --- 2. デザイン（仕様：中央・細字・重なり防止） ---
st.set_page_config(page_title="献だけ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300&display=swap');
    
    /* 基本フォント（丸み・細字）を全体に。アイコン（span）への干渉を避ける */
    html, body, [class*="css"], p, div:not([data-testid="stExpanderIcon"]) {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }

    /* タイトルエリアをブロック要素として独立させ、物理的な高さを確保 */
    .title-container {
        display: block;
        text-align: center;
        padding-top: 3rem;
        padding-bottom: 5rem; /* 下の要素を確実に押し下げる */
        width: 100%;
    }
    .title-font {
        font-size: 3.5rem;
        font-weight: 300;
        letter-spacing: 0.2em;
    }
    
    /* 太字（Bold）の徹底解除 */
    b, strong, th { font-weight: 300 !important; }
</style>
<div class="title-container">
    <div class="title-font">献 だけ</div>
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
                # 標準のselectboxを使用（デザインはCSSで調整済み）
                val = st.selectbox(cat, ["選択なし"] + options, key=f"v2_{tabs_list[i]}_{cat}")
                day_plan[cat] = val
        selected_plan[tabs_list[i]] = day_plan

# --- 4. 買い物リスト ＆ メニュー表 ---
st.write("")
if st.button("1週間のメニュー表と買い物リストを作成"):
    st.divider()
    res_col1, res_col2 = st.columns([3, 2])
    
    all_ings = []
    with res_col1:
        st.write("📖 1週間のメニュー表")
        table_data = []
        for day, dishes in selected_plan.items():
            row = {"曜日": day}
            row.update(dishes)
            table_data.append
