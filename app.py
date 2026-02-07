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

# --- 2. デザイン定義 (指示通りノイズを消し、Noto Sans JPを適用) ---
st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    
    /* フォント指定：Noto Sans JP */
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    
    /* ノイズ消去：ヘッダーとサイドバーボタンを隠す */
    header[data-testid="stHeader"] { background: transparent !important; color: transparent !important; pointer-events: none; }
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

# --- 4. 認証フロー (ログイン画面もデザイン統一) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    df_users, user_sha = get_github_file(USER_FILE)
    with st.form("login"):
        u = st.text_input("メールアドレス", key="ul", autocomplete="email")
        p = st.text_input("パスワード", type="password", key="pl", autocomplete="current-password")
        if st.form_submit_button("ログイン", use_container_width=True):
            if not df_users.empty and u in df_users["username"].values:
                st.session_state.update({"authenticated": True, "username": u})
                st.rerun()
            else:
                st.error("認証に失敗しました")
    st.stop()

# --- 5. メインアプリ ---
st.markdown('<div style="text-align:right"><small>Logged in as: ' + st.session_state['username'] + '</small></div>', unsafe_allow_html=True)
st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

df_menu, menu_sha = get_github_file(FILE)

t_plan, t_hist, t_manage = st.tabs(["📋 献立作成", "📜 履歴", "⚙️ メニュー管理"])

with t_plan:
    # 日曜スタート仕様：(今日の日数 + 1) % 7 で直近の日曜を出す
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日曜日）", value=default_sun)
    
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    d_tabs = st.tabs(day_labels)
    cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
    for i, tab in enumerate(d_tabs):
        with tab:
            st.markdown(f"##### {(start_date + timedelta(days=i)).strftime('%Y/%m/%d')} ({day_labels[i]})")
            for c in cats:
                opts = ["なし"] + (df_menu[df_menu["カテゴリー"] == c]["料理名"].tolist() if not df_menu.empty else [])
                st.selectbox(c, opts, key=f"sel_{i}_{c}")
    st.button("確定して買い物リストを生成", type="primary", use_container_width=True)

with t_manage:
    st.subheader("登録メニューの編集・削除")
    if not df_menu.empty:
        # 編集可能なモダンな表。列順も仕様通り
        edited_df = st.data_editor(
            df_menu,
            column_order=["料理名", "カテゴリー", "材料"],
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="m_editor"
        )
        if st.button("変更を確定してGitHubへ保存", type="primary", use_container_width=True):
            save_to_github(edited_df, FILE, "Update menu data", menu_sha)
            st.success("メニューを更新しました")
            st.rerun()
    
    with st.expander("＋ 新しい料理を個別に追加"):
        with st.form("add_new", clear_on_submit=True):
            n_cat = st.selectbox("カテゴリー", ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"])
            n_name = st.text_input("料理名")
            n_ing = st.text_area("材料")
            if st.form_submit_button("この内容で保存"):
                new_row = pd.DataFrame([[n_name, n_cat, n_ing]], columns=["料理名", "カテゴリー", "材料"])
                updated = pd.concat([df_menu, new_row], ignore_index=True)
                save_to_github(updated, FILE, f"Add {n_name}", menu_sha)
                st.rerun()
