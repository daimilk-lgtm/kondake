import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- 0. 設定 ---
REPO = "daimilk-lgtm/kondake"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 1. 読み込み関数 ---
def get_github_data(filename):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            content_data = r.json()
            raw = base64.b64decode(content_data["content"]).decode("utf-8-sig")
            # タブ区切りとカンマ区切りの両方に対応する工夫
            sep = "\t" if "\t" in raw else ","
            df = pd.read_csv(io.StringIO(raw), sep=sep)
            return df, content_data["sha"]
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
    return pd.DataFrame(), None

# --- 2. ログインUI（デバッグ機能付き） ---
def login_ui():
    st.title("ログイン")
    
    # 最新のユーザーリストを強制的に取得
    df_users, _ = get_github_data(USER_FILE)
    
    # 【デバッグ用】今の登録状況をひっそり表示（確認したら消してください）
    with st.expander("登録状況の確認（デバッグ用）"):
        st.write("現在のusers.csvの中身:", df_users)

    l_email = st.text_input("メールアドレス")
    l_pw = st.text_input("パスワード", type="password")
    
    if st.button("ログイン", type="primary", use_container_width=True):
        if not df_users.empty:
            # 前後の余計な空白を削除して比較
            df_users['email'] = df_users['email'].astype(str).str.strip()
            df_users['password'] = df_users['password'].astype(str).str.strip()
            
            match = df_users[(df_users["email"] == l_email.strip()) & (df_users["password"] == l_pw.strip())]
            
            if not match.empty:
                st.session_state.logged_in = True
                st.session_state.u_email = l_email
                st.session_state.u_plan = match.iloc[0]["plan"]
                st.success("ログイン成功！")
                st.rerun()
            else:
                st.error("一致するユーザーが見つかりません。入力ミスか、登録がGitHubに反映されていない可能性があります。")
        else:
            st.error("ユーザーリストが空です。先に登録を行ってください。")

# 制御ロジック
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_ui()
else:
    st.write(f"ようこそ、{st.session_state.u_email}さん！")
    if st.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()
