import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials

# --- 1. 接続・認証 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_data(ttl=10) # 開発中は短めに設定（10秒）
def get_data():
    try:
        creds_dict = dict(st.secrets)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        
        spread = Spread("献だけデータ", creds=creds)
        
        # 【重要】シート名を明示的に「シート1」と指定し、確実にデータを取得する
        df = spread.sheet_to_df(sheet="シート1", index=None)
        
        # もしデータが空なら、空のDataFrameを返す（エラー防止）
        if df.empty:
            return spread, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])
            
        return spread, df
    except Exception as e:
        # エラー時は画面に表示させて原因を特定する
        st.error(f"データ読み込みエラー: {e}")
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

spread, df_master = get_data()

# --- 2. デザイン：等間隔タイトル & アイコン保護 ---
st.set_page_config(page_title="献だけ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300&display=swap');
    
    html, body, [class*="css"], p, div:not([data-testid="stExpanderIcon"]), select, input {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }

    .title-wrapper {
        text-align: center;
        padding: 4rem 0 3rem 0;
    }
    .title-text {
        font-size: 3.5rem;
        font-weight: 300;
        letter-spacing: 0.5em;
        margin-right: -0.5em;
        color: #333;
    }
    b, strong, th, label { font-weight: 300 !important; }
</style>
<div class="title-wrapper">
    <div class="title-text">献だけ</div>
</div>
""", unsafe_allow_html=True)

# --- 3. 献立計画 ---
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
                # フィルタリング（確実に一致させるためスペースを除去）
                if not df_master.empty:
                    df_master["カテゴリー"] = df_master["カテゴリー"].str.strip()
                    options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                else:
                    options = []
                
                val = st.selectbox(cat, ["選択なし"] + options, key=f"v4_{tabs_list[i]}_{cat}")
                day_plan[cat] = val
        selected_plan[tabs_list[i]] = day_plan

# --- 4. 買い物リスト ＆ メニュー表 ---
st.write("")
if st.button("こんだけ作成", key="main_btn"):
    st.divider()
    res_col1, res_col2 = st.columns([3, 2])
    
    all_ingredients = []
    with res_col1:
        st.write("📖 1週間のメニュー表")
        display_data = []
        for day, dishes in selected_plan.items():
            row_data = {"曜日": day}
            row_data.update(dishes)
            display_data.append(row_data)
            
            for dish_name in dishes.values():
                if dish_name != "選択なし" and not df_master.empty:
                    match = df_master[df_master["料理名"] == dish_name]
                    if not match.empty:
                        ing_raw = match["材料"].iloc[0]
                        if ing_raw:
                            items = ing_raw.replace("、", "\n").replace(",", "\n").splitlines()
                            all_ingredients.extend([x.strip() for x in items if x.strip()])
        
        st.dataframe(pd.DataFrame(display_data), hide_index=True, use_container_width=True)

    with res_col2:
        st.write("🛒 買い物リスト")
        unique_ings = sorted(list(set(all_ingredients)))
        if unique_ings:
            for item in unique_ings:
                st.checkbox(item, key=f"buy_v4_{item}")
        else:
            st.write("メニューを選んでください。")

# --- 5. 追加・修正機能 ---
st.write("---")
with st.expander("📝 料理の追加・内容の修正"):
    with st.form("editor_v4", clear_on_submit=True):
        f_c1, f_c2 = st.columns(2)
        with f_c1:
            name = st.text_input("料理名")
        with f_c2:
            cat = st.selectbox("カテゴリー", categories)
        ing = st.text_area("材料（「、」で区切る）")
        
        if st.form_submit_button("保存"):
            if name and spread:
                new_df = df_master[df_master["料理名"] != name]
                add_data = pd.DataFrame([[name, cat, ing]], columns=["料理名", "カテゴリー", "材料"])
                final_df = pd.concat([new_df, add_data], ignore_index=True)
                # シート名を指定して保存
                spread.df_to_sheet(final_df, index=False, replace=True, sheet="シート1")
                st.success(f"「{name}」を保存しました。")
                st.cache_data.clear()
