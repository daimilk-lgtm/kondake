import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. 接続・認証（安定動作中） ---
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

# --- 2. 視覚設計（仕様：中央タイトル・細字・重なり防止・アイコン保護） ---
st.set_page_config(page_title="献だけ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300&display=swap');
    
    /* 基本フォント設定：アイコンや特殊クラスを除外して適用 */
    html, body, [class*="css"], p, div:not([data-testid="stExpanderIcon"]), select, input {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }

    /* タイトルエリア：物理的な余白を確保し、重なりを完全に防ぐ */
    .title-wrapper {
        text-align: center;
        padding: 3rem 0 4rem 0;
    }
    .title-text {
        font-size: 3.5rem;
        font-weight: 300;
        letter-spacing: 0.2em;
    }
    
    /* 太字（Bold）を徹底的に無効化 */
    b, strong, th, label { font-weight: 300 !important; }
</style>
<div class="title-wrapper">
    <div class="title-text">献 だけ</div>
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
                val = st.selectbox(cat, ["選択なし"] + options, key=f"v3_{tabs_list[i]}_{cat}")
                day_plan[cat] = val
        selected_plan[tabs_list[i]] = day_plan

# --- 4. 買い物リスト ＆ メニュー表（バグを修正） ---
st.write("")
if st.button("1週間のメニュー表と買い物リストを作成"):
    st.divider()
    res_col1, res_col2 = st.columns([3, 2])
    
    all_ingredients = []
    with res_col1:
        st.write("📖 1週間のメニュー表")
        display_list = [] # 正しくデータを格納するリスト
        for day, dishes in selected_plan.items():
            row_data = {"曜日": day}
            row_data.update(dishes)
            # 修正ポイント：関数名ではなく「データ」を追加
            display_list.append(row_data) 
            
            for dish_name in dishes.values():
                if dish_name != "選択なし" and not df_master.empty:
                    match = df_master[df_master["料理名"] == dish_name]
                    if not match.empty:
                        ing_raw = match["材料"].iloc[0]
                        if ing_raw:
                            # 材料を分解
                            items = ing_raw.replace("、", "\n").replace(",", "\n").splitlines()
                            all_ingredients.extend([x.strip() for x in items if x.strip()])
        
        # 表としてクリーンに表示
        st.dataframe(pd.DataFrame(display_list), hide_index=True, use_container_width=True)

    with res_col2:
        st.write("🛒 買い物リスト")
        unique_ings = sorted(list(set(all_ingredients)))
        if unique_ings:
            for item in unique_ings:
                st.checkbox(item, key=f"buy_v3_{item}")
        else:
            st.write("メニューを選んでください。")

# --- 5. 追加・修正 ---
st.write("---")
with st.expander("📝 料理の追加・内容の修正"):
    with st.form("editor_v3", clear_on_submit=True):
        f
