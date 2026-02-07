import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta

# --- 0. 基本情報 ---
VERSION = "1.3.1"
REPO = "daimilk-lgtm/kondake"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 1. GitHub連携関数 (タブ区切り "\t" をデフォルトに設定) ---
def get_github_data(filename, sep="\t"):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            content_data = r.json()
            raw = base64.b64decode(content_data["content"]).decode("utf-8-sig")
            # 空ファイルの場合は空のDFを返す
            if not raw.strip() or raw.strip() == "email\tpassword\tplan":
                return pd.DataFrame(columns=["email", "password", "plan"]), content_data["sha"]
            df = pd.read_csv(io.StringIO(raw), sep=sep)
            return df, content_data["sha"]
    except Exception as e:
        st.error(f"読み込みエラー: {e}")
    return pd.DataFrame(columns=["email", "password", "plan"]), None

def save_to_github(df, filename, message, current_sha=None, sep="\t"):
    # インデックスを含めず、タブ区切りでCSV化
    csv_content = df.to_csv(index=False, encoding="utf-8-sig", sep=sep)
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha:
        data["sha"] = current_sha
    
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 2. ログイン・登録UI ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_ui():
    st.title("献だけ 会員登録・ログイン")
    tab_login, tab_signup = st.tabs(["ログイン", "新規ユーザー登録"])
    
    # ユーザー名簿をロード
    df_users, user_sha = get_github_data(USER_FILE)

    with tab_signup:
        st.subheader("新しいアカウントを作る")
        new_email = st.text_input("メールアドレス")
        new_pw = st.text_input("パスワード", type="password")
        if st.button("登録を実行", use_container_width=True):
            if new_email and new_pw:
                # 重複チェック
                if not df_users.empty and new_email in df_users["email"].values:
                    st.warning("このメールアドレスは登録済みです。")
                else:
                    new_row = pd.DataFrame([[new_email, new_pw, "free"]], columns=["email", "password", "plan"])
                    updated_df = pd.concat([df_users, new_row], ignore_index=True)
                    
                    # GitHubへ保存実行
                    status = save_to_github(updated_df, USER_FILE, f"Register: {new_email}", user_sha)
                    if status == 200 or status == 201:
                        st.success("GitHubへの登録に成功しました！ログインタブから進んでください。")
                        st.balloons()
                    else:
                        st.error(f"保存失敗 (エラーコード: {status})。リポジトリの権限設定を確認してください。")
            else:
                st.error("メールアドレスとパスワードを入力してください。")

    with tab_login:
        st.subheader("ログイン")
        l_email = st.text_input("メールアドレス", key="l_in")
        l_pw = st.text_input("パスワード", type="password", key="p_in")
        if st.button("ログインする", type="primary", use_container_width=True):
            if not df_users.empty:
                match = df_users[(df_users["email"] == l_email) & (df_users["password"] == l_pw)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.u_email = l_email
                    st.session_state.u_plan = match.iloc[0]["plan"]
                    st.rerun()
                else:
                    st.error("メールアドレスまたはパスワードが正しくありません。")
            else:
                st.error("ユーザーデータがありません。")

# --- メイン制御 ---
if not st.session_state.logged_in:
    login_ui()
else:
    st.sidebar.write(f"Logged in: {st.session_state.u_email}")
    if st.sidebar.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()
    
    st.success(f"{st.session_state.u_email} さん、こんにちは！")
    # ここに本来の献立アプリのコードを記述
