import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta

# --- 1. 接続・デザイン設定 (省略なし) ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    header[data-testid="stHeader"] { background: transparent !important; color: transparent !important; }
    [data-testid="stSidebarCollapseButton"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. データ取得関数 ---
def get_github_file(filename):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            return pd.read_csv(io.StringIO(raw))
    except: pass
    return pd.DataFrame()

# --- 3. メイン画面 ---
st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
df_menu = get_github_file(FILE)

t_plan, t_hist, t_manage = st.tabs(["📋 献立作成", "📜 履歴", "⚙️ メニュー管理"])

with t_plan:
    # 日曜スタート
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日）", value=default_sun)
    
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    d_tabs = st.tabs(day_labels)
    
    # 選択内容を保持する辞書
    selections = {}
    
    if not df_menu.empty:
        for i, tab in enumerate(d_tabs):
            with tab:
                st.markdown(f"##### {(start_date + timedelta(days=i)).strftime('%Y/%m/%d')} ({day_labels[i]})")
                day_sel = []
                for c in ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]:
                    opts = ["なし"] + df_menu[df_menu["カテゴリー"] == c]["料理名"].tolist()
                    sel = st.selectbox(c, opts, key=f"s_{i}_{c}")
                    if sel != "なし":
                        day_sel.append(sel)
                selections[i] = day_sel

        # --- 買い物リスト生成ロジック ---
        if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
            all_selected_dishes = [dish for dishes in selections.values() for dish in dishes]
            
            if not all_selected_dishes:
                st.warning("メニューが選択されていません。")
            else:
                st.markdown("---")
                st.subheader("🛒 買い物リスト")
                
                # 選択された料理名に一致する「材料」を抽出
                ingredients_list = []
                for dish in all_selected_dishes:
                    row = df_menu[df_menu["料理名"] == dish]
                    if not row.empty and pd.notna(row.iloc[0]["材料"]):
                        # カンマや改行で区切られた材料をバラす
                        items = re.split(r'[,、\n]', str(row.iloc[0]["材料"]))
                        ingredients_list.extend([item.strip() for item in items if item.strip()])
                
                if ingredients_list:
                    # 重複を除去して表示
                    unique_ingredients = sorted(list(set(ingredients_list)))
                    for item in unique_ingredients:
                        st.checkbox(item, key=f"check_{item}")
                    
                    # コピー用テキストエリア
                    st.text_area("コピー用リスト", value="\n".join(unique_ingredients), height=150)
                else:
                    st.info("選択されたメニューに材料が登録されていません。")

with t_manage:
    # (以前の管理画面コードと同じため省略可だが、動くように data_editor を配置)
    st.data_editor(df_menu, use_container_width=True, hide_index=True)
