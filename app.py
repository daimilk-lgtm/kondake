import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# --- 0. 基本情報・設定 ---
VERSION = "1.3.2"
REPO = "daimilk-lgtm/kondake"
USER_FILE = "users.csv"
MENU_FILE = "menu.csv"
HIST_FILE = "history.csv"
DICT_FILE = "ingredients.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 1. GitHub連携関数 ---
def get_github_data(filename, is_user=False):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            content_data = r.json()
            raw = base64.b64decode(content_data["content"]).decode("utf-8-sig")
            
            # ユーザーファイルの場合は「空白区切り」かつ「全て文字列」として読み込む
            if is_user:
                df = pd.read_csv(io.StringIO(raw), sep=r'\s+', engine='python', dtype=str)
            else:
                df = pd.read_csv(io.StringIO(raw))
            
            df.columns = [c.strip() for c in df.columns]
            return df, content_data["sha"]
    except: pass
    return pd.DataFrame(), None

def save_to_github(df, filename, message, current_sha=None, is_user=False):
    # ユーザーファイルはタブ区切り、それ以外はカンマ区切り
    sep = "\t" if is_user else ","
    csv_content = df.to_csv(index=False, encoding="utf-8-sig", sep=sep)
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 2. 認証ロジック ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_ui():
    st.markdown('<h1 style="text-align:center; font-weight:100;">献だけ</h1>', unsafe_allow_html=True)
    tab_login, tab_signup = st.tabs(["ログイン", "新規登録"])
    
    df_users, user_sha = get_github_data(USER_FILE, is_user=True)

    with tab_signup:
        st.subheader("アカウント作成")
        new_email = st.text_input("メールアドレス", key="reg_email")
        new_pw = st.text_input("パスワード", type="password", key="reg_pw")
        if st.button("新規登録を実行", use_container_width=True):
            if new_email and new_pw:
                if not df_users.empty and new_email in df_users["email"].values:
                    st.error("このメールアドレスは既に登録されています。")
                else:
                    new_user = pd.DataFrame([[new_email, new_pw, "free"]], columns=["email", "password", "plan"])
                    updated_users = pd.concat([df_users, new_user], ignore_index=True)
                    if save_to_github(updated_users, USER_FILE, f"Register {new_email}", user_sha
