import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta
import re  # 確実にインポート

# --- 1. 接続・デザイン設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
USER_FILE = "users.csv"
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
            df = pd.read_csv(io.StringIO(raw))
            if filename == USER_FILE and 'email' in df.columns:
                df = df.rename(columns={'email': 'username'})
            return df, r.json()["sha"]
    except: pass
    return pd.DataFrame(), None

# --- 3. 認証・メイン処理 ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    df_users, _ = get_github_file(USER_FILE)
    with st.form("login"):
        u = st.text_input("メールアドレス", key="ul")
        p = st.text_input("パスワード", type="password", key="pl")
        if st.form_submit_button("ログイン", use_container_width=True):
            if not df_users.empty and u in df_users["username"].values:
                st.session_state.update({"authenticated": True, "username": u})
                st.rerun()
    st.stop()

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
df_menu, menu_sha = get_github_file(FILE)

t_plan, t_hist, t_manage = st.tabs(["📋 献立作成", "📜 履歴", "⚙️ メニュー管理"])

with t_plan:
    # 日曜スタート仕様
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日）", value=default_sun)
    
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    d_tabs = st.tabs(day_labels)
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

        if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
            all_dishes = [d for ds in selections.values() for d in ds]
            if all_dishes:
                st.markdown("---")
                st.subheader("🛒 買い物リスト")
                
                ing_all = []
                for dish in all_dishes:
                    row = df_menu[df_menu["料理名"] == dish]
                    if not row.empty and pd.notna(row.iloc[0]["材料"]):
                        # 材料を分割 (カンマ、読点、改行対応)
                        items = re.split(r'[,、\n]', str(row.iloc[0]["材料"]))
                        ing_all.extend([it.strip() for it in items if it.strip()])
                
                if ing_all:
                    unique_ings = sorted(list(set(ing_all)))
                    for item in unique_ings:
                        st.checkbox(item, key=f"chk_{item}")
                    st.text_area("コピー用", value="\n".join(unique_ings), height=150)
                else:
                    st.info("材料が登録されていません。")
            else:
                st.warning("献立を選択してください。")

with t_manage:
    if not df_menu.empty:
        st.subheader("メニュー編集")
        # 編集可能な表を表示
        edited_df = st.data_editor(
            df_menu,
            column_order=["料理名", "カテゴリー", "材料"],
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )
        if st.button("GitHubへ保存"):
            # 保存処理... (省略)
            pass
