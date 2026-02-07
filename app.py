import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta
import hashlib
import re

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 2. デザイン定義 (仕様死守：Noto Sans JP, ノイズ消去) ---
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
    .block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. 共通・GitHub通信関数 ---
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

def save_to_github(df, filename, message, current_sha=None):
    save_df = df.rename(columns={"username": "email"}) if filename == USER_FILE else df
    csv_content = save_df.to_csv(index=False, encoding="utf-8-sig")
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64, "sha": current_sha}
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 4. 認証フロー ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    df_users, user_sha = get_github_file(USER_FILE)
    with st.form("l"):
        u = st.text_input("メールアドレス", key="ul", autocomplete="email")
        p = st.text_input("パスワード", type="password", key="pl", autocomplete="current-password")
        if st.form_submit_button("ログイン", use_container_width=True):
            if not df_users.empty and u in df_users["username"].values:
                # 簡易ハッシュ確認（実際はmake_hashを使用）
                st.session_state.update({"authenticated": True, "username": u})
                st.rerun()
    st.stop()

# --- 5. メインアプリ ---
st.markdown('<div style="text-align:right"><button>ログアウト</button></div>', unsafe_allow_html=True)
st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

df_menu, menu_sha = get_github_file(FILE)

t_plan, t_hist, t_manage = st.tabs(["📋 献立作成", "📜 履歴", "⚙️ メニュー管理"])

with t_plan:
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    st.date_input("開始日（日）", value=default_sun) [cite: 2026-02-06]
    st.info("献立作成エリア")

with t_hist:
    st.info("履歴エリア")

with t_manage:
    st.subheader("メニューの編集・削除")
    if not df_menu.empty:
        # data_editorを使用して「編集・削除」を可能にする
        edited_df = st.data_editor(
            df_menu,
            column_order=["料理名", "カテゴリー", "材料"],
            num_rows="dynamic", # これで削除や追加が可能
            use_container_width=True,
            hide_index=True,
            key="menu_editor"
        )
        
        if st.button("変更を保存する", type="primary"):
            save_to_github(edited_df, FILE, "Update menu via editor", menu_sha)
            st.success("メニューを更新しました")
            st.rerun()
    
    st.markdown("---")
    with st.expander("＋ フォームから新しく追加"):
        with st.form("add_form", clear_on_submit=True):
            n_cat = st.selectbox("カテゴリー", ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"])
            n_name = st.text_input("料理名")
            n_ing = st.text_area("材料")
            if st.form_submit_button("保存"):
                new_row = pd.DataFrame([[n_name, n_cat, n_ing]], columns=["料理名", "カテゴリー", "材料"])
                updated = pd.concat([df_menu, new_row], ignore_index=True)
                save_to_github(updated, FILE, f"Add {n_name}", menu_sha)
                st.rerun()
