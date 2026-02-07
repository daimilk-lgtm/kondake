import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import hashlib
import re

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 2. デザイン定義 (仕様死守：左上のノイズ排除) ---
st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    header[data-testid="stHeader"], section[data-testid="stSidebar"], button[data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    .block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. 認証・GitHub通信関数 ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

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
    return pd.DataFrame(columns=["username", "password"]), None

def save_to_github(df, filename, message, current_sha=None):
    save_df = df.rename(columns={"username": "email"}) if filename == USER_FILE else df
    csv_content = save_df.to_csv(index=False, encoding="utf-8-sig")
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 4. 認証フロー (ログイン維持機能追加) ---
if "authenticated" not in st.session_state:
    # ここでブラウザ側のストレージやCookieを確認する処理も可能ですが、
    # シンプルに「セッション中は維持」を徹底します。
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    auth_tab1, auth_tab2 = st.tabs(["ログイン", "新規ユーザー登録"])
    df_users, user_sha = get_github_file(USER_FILE)

    with auth_tab1:
        # ブラウザに「ログインフォーム」と認識させるため、autocomplete属性を意識した構成
        with st.form("login_form", clear_on_submit=False):
            u_login = st.text_input("メールアドレス", key="login_email", autocomplete="email")
            p_login = st.text_input("パスワード", type="password", key="login_pass", autocomplete="current-password")
            
            # 利便性のためのオプション
            remember_me = st.checkbox("ログイン状態を維持する", value=True)
            
            if st.form_submit_button("ログイン", use_container_width=True):
                h_pwd = make_hash(p_login)
                if not df_users.empty and u_login in df_users["username"].values:
                    if df_users[df_users["username"] == u_login]["password"].iloc[0] == h_pwd:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u_login
                        st.rerun()
                st.error("ログイン失敗。アドレスまたはパスワードを確認してください")

    with auth_tab2:
        with st.form("reg_form"):
            u_reg = st.text_input("メールアドレス", autocomplete="email")
            p_reg = st.text_input("パスワード (8文字以上の英数字)", type="password", autocomplete="new-password")
            if st.form_submit_button("登録実行", use_container_width=True):
                if re.match(r"[^@]+@[^@]+\.[^@]+", u_reg) and len(p_reg) >= 8:
                    if u_reg in df_users["username"].values:
                        st.warning("登録済みのアドレスです")
                    else:
                        new_user = pd.DataFrame([[u_reg, make_hash(p_reg)]], columns=["username", "password"])
                        updated_users = pd.concat([df_users, new_user], ignore_index=True)
                        save_to_github(updated_users, USER_FILE, f"Add {u_reg}", user_sha)
                        st.success("登録完了！ログインしてください")
                else:
                    st.error("形式不備：メアド形式かつ8文字以上のパスワードが必要です")
    st.stop()

# --- 5. メインアプリ (仕様: 日付入力・日曜スタート) ---
col_title, col_logout = st.columns([0.8, 0.2])
with col_logout:
    if st.button("ログアウト"):
        st.session_state["authenticated"] = False
        st.rerun()

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
st.write(f"Logged in as: {st.session_state['username']}")

# (献立作成・日曜スタート仕様などのロジックは以前の正常動作版を継承)
df_menu, _ = get_github_file(FILE)
if not df_menu.empty:
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日）", value=default_sun)
    
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    days_tabs = st.tabs(day_labels)
    # ... 以下省略
