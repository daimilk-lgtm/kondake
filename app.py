import streamlit as st
import pandas as pd
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials
import json

# --- 1. 接続・認証設定 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_data(ttl=60)
def get_data():
    try:
        s_dict = dict(st.secrets)
        # JSONをそのまま貼った場合と、バラで貼った場合の両方に対応
        if "json_data" in s_dict:
            info = json.loads(s_dict["json_data"])
        else:
            info = s_dict
        
        # 秘密鍵の改行コードを正しく処理
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
            
        creds = Credentials.from_service_account_info(info, scopes=scope)
        # スプレッドシート名「献だけデータ」を開く
        spread = Spread("献だけデータ", creds=creds)
        
        # 明示的に「シート1」を読み込む
        df = spread.sheet_to_df(sheet="シート1", index=None)
        
        # カテゴリーの空白を削除して一致率を高める
        if not df.empty and "カテゴリー" in df.columns:
            df["カテゴリー"] = df["カテゴリー"].str.strip()
            
        return spread, df
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return None, pd.DataFrame(columns=["料理名", "カテゴリー", "材料"])

# データの読み込み
spread, df_master = get_data()

# --- 2. 画面デザイン ---
st.set_page_config(page_title="献だけ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300&display=swap');
    html, body, [class*="css"], p, div:not([data-testid="stExpanderIcon"]), select, input {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .title-wrapper { text-align: center; padding: 3rem 0; }
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
                # 各カテゴリーに一致する料理をリスト化
                if not df_master.empty:
                    options = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                else:
                    options = []
                
                # セレクトボックス
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
            
            # 材料の集計
            for dish_name in dishes.values():
                if dish_name != "選択なし":
                    match = df_master[df_master["料理名"] == dish_name]
                    if not match.empty:
                        ing_raw = match["材料"].iloc[0]
                        if ing_raw:
                            # 区切り文字を統一して分割
                            items = ing_raw.replace("、", "\n").replace(",", "\n").splitlines()
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

# --- 5. データベース管理（追加機能） ---
st.write("---")
with st.expander("📝 料理の追加・編集"):
    with st.form("edit_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("料理名")
        with c2:
            new_cat = st.selectbox("カテゴリー", categories)
        new_ing = st.text_area("材料（「、」で区切る）")
        
        if st.form_submit_button("スプレッドシートに保存"):
            if new_name and spread:
                # 既存データを削除して新しいデータを追加（上書き対応）
                other_data = df_master[df_master["料理名"] != new_name]
                add_data = pd.DataFrame([[new_name, new_cat, new_ing]], columns=["料理名", "カテゴリー", "材料"])
                final_df = pd.concat([other_data, add_data], ignore_index=True)
                
                # スプレッドシートへ書き込み
                spread.df_to_sheet(final_df, index=False, replace=True, sheet="シート1")
                st.success(f"「{new_name}」を保存しました！")
                st.cache_data.clear()
                st.rerun()
