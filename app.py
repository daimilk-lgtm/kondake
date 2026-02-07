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
DICT_FILE = "ingredients.csv"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 2. デザイン定義 (左上のノイズを物理的に封じる) ---
st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    
    /* 左上の文字化け（double_arrow等）を強制非表示 */
    header, [data-testid="stSidebar"], [data-testid="stSidebarCollapseButton"] {
        display: none !important;
        visibility: hidden !important;
    }
    .block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. 認証・GitHub通信関数 ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_strong_password(pwd):
    return len(pwd) >= 8 and any(c.isalpha() for c in pwd) and any(c.isdigit() for c in pwd)

def get_github_file(filename):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(raw))
            # カラム名の不一致(email/username)を吸収
            if filename == USER_FILE:
                df = df.rename(columns={"email": "username"})
            return df, r.json()["sha"]
    except: pass
    return pd.DataFrame(columns=["username", "password"]), None

def save_to_github(df, filename, message, current_sha=None):
    # 保存時は元のヘッダー(email)に合わせる
    save_df = df.rename(columns={"username": "email"})
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
    auth_tab1, auth_tab2 = st.tabs(["ログイン", "新規ユーザー登録"])
    df_users, user_sha = get_github_file(USER_FILE)

    with auth_tab1:
        with st.form("login_form"):
            u_login = st.text_input("メールアドレス")
            p_login = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン", use_container_width=True):
                h_pwd = make_hash(p_login)
                if not df_users.empty and "username" in df_users.columns:
                    match = df_users[(df_users["username"] == u_login) & (df_users["password"] == h_pwd)]
                    if not match.empty:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u_login
                        st.rerun()
                st.error("ログイン失敗。内容を確認してください")

    with auth_tab2:
        with st.form("reg_form"):
            u_reg = st.text_input("メールアドレス")
            p_reg = st.text_input("パスワード (8文字以上の英数字)", type="password")
            if st.form_submit_button("登録実行", use_container_width=True):
                if not is_valid_email(u_reg):
                    st.error("正しいメールアドレスを入力してください")
                elif not is_strong_password(p_reg):
                    st.error("パスワード条件を満たしていません")
                elif u_reg in df_users["username"].values:
                    st.warning("登録済みのアドレスです")
                else:
                    new_user = pd.DataFrame([[u_reg, make_hash(p_reg)]], columns=["username", "password"])
                    updated_users = pd.concat([df_users, new_user], ignore_index=True)
                    status = save_to_github(updated_users, USER_FILE, f"Add {u_reg}", user_sha)
                    if status == 201 or status == 200:
                        st.success("登録完了！ログインしてください")
                    else:
                        st.error(f"保存失敗(Code:{status})。Token権限を確認してください")
    st.stop()

# --- 5. メインアプリ (仕様死守: 日付入力・日曜スタート) ---
# (中略: メインコンテンツ部分は以前の正常動作コードを維持)
st.button("ログアウト", on_click=lambda: st.session_state.update({"authenticated": False}))
st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
st.write(f"Login: {st.session_state['username']}")
