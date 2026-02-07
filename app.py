import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta

# --- 0. 基本情報 ---
VERSION = "1.3.0"
REPO = "daimilk-lgtm/kondake"
USER_FILE = "users.csv"
MENU_FILE = "menu.csv"
HIST_FILE = "history.csv"
DICT_FILE = "ingredients.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 1. GitHub連携関数 ---
def get_github_data(filename, sep=","):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(raw), sep=sep)
            return df, r.json()["sha"]
    except: pass
    return pd.DataFrame(), None

def save_to_github(df, filename, message, current_sha=None, sep=","):
    csv_content = df.to_csv(index=False, encoding="utf-8-sig", sep=sep)
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 2. ログイン・登録処理 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.session_state.user_plan = "free"

def login_ui():
    st.markdown('<h1 style="text-align:center;">献だけ ログイン</h1>', unsafe_allow_html=True)
    tab_login, tab_signup = st.tabs(["ログイン", "新規ユーザー登録"])
    
    # ユーザーデータ取得 (タブ区切り)
    df_users, user_sha = get_github_data(USER_FILE, sep="\t")

    with tab_signup:
        st.subheader("アカウント作成")
        new_email = st.text_input("メールアドレス (ID)")
        new_pw = st.text_input("パスワード", type="password")
        if st.button("新規登録", use_container_width=True):
            if new_email and new_pw:
                if not df_users.empty and new_email in df_users["email"].values:
                    st.error("このメールアドレスは既に登録されています。")
                else:
                    new_user = pd.DataFrame([[new_email, new_pw, "free"]], columns=["email", "password", "plan"])
                    updated_users = pd.concat([df_users, new_user], ignore_index=True)
                    if save_to_github(updated_users, USER_FILE, f"Add user {new_email}", user_sha, sep="\t") == 200:
                        st.success("登録完了！ログインしてください。")
                    else:
                        st.error("GitHubへの保存に失敗しました。")
            else:
                st.warning("入力してください。")

    with tab_login:
        st.subheader("ログイン")
        login_email = st.text_input("メールアドレス", key="l_email")
        login_pw = st.text_input("パスワード", type="password", key="l_pw")
        if st.button("ログイン", type="primary", use_container_width=True):
            if not df_users.empty:
                user_match = df_users[(df_users["email"] == login_email) & (df_users["password"] == login_pw)]
                if not user_match.empty:
                    st.session_state.logged_in = True
                    st.session_state.user_email = login_email
                    st.session_state.user_plan = user_match.iloc[0]["plan"]
                    st.rerun()
                else:
                    st.error("IDまたはパスワードが違います。")
            else:
                st.error("ユーザーが存在しません。先に登録してください。")

# --- 3. メインアプリ実行 ---
if not st.session_state.logged_in:
    login_ui()
else:
    # ログアウトボタンをサイドバーに
    if st.sidebar.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()
    
    # 無料プランなら広告を出す
    if st.session_state.user_plan == "free":
        st.sidebar.info("💡 プレミアムなら広告なし！")
        st.info("【無料版】本日のオススメ食材は『鶏むね肉』です！(広告枠)")

    # --- ここに以前の献立アプリのコードを続ける ---
    st.write(f"ようこそ {st.session_state.user_email} さん ({st.session_state.user_plan}プラン)")
    # (既存のdf_menu読み込みやタブのロジックをここに配置)
