import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- 0. 設定 ---
REPO = "daimilk-lgtm/kondake"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 1. 読み込み関数 (自動判別・ズレ防止版) ---
def get_github_data(filename):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            content_data = r.json()
            raw = base64.b64decode(content_data["content"]).decode("utf-8-sig")
            
            # 【対策1】区切り文字（タブ、カンマ、スペース）を自動判別
            # engine='python' を使うことで、曖昧な区切りにも対応します
            df = pd.read_csv(io.StringIO(raw), sep=r'\s+|,', engine='python')
            
            # 【対策2】列名の前後に空白があれば削除
            df.columns = [c.strip() for c in df.columns]
            return df, content_data["sha"]
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
    return pd.DataFrame(), None

# --- 2. ログインUI ---
def login_ui():
    st.title("ログイン")
    
    df_users, _ = get_github_data(USER_FILE)
    
    with st.expander("登録状況の確認（ここが正しく並んでいればOK）"):
        st.write(df_users)

    l_email = st.text_input("メールアドレス")
    # パスワードは 0 から始まる可能性があるので、数値ではなく文字列として扱います
    l_pw = st.text_input("パスワード", type="password")
    
    if st.button("ログイン", type="primary", use_container_width=True):
        if not df_users.empty:
            # 【対策3】全データを文字列に変換し、前後の空白を徹底的に消す
            df_users = df_users.astype(str).apply(lambda x: x.str.strip())
            
            # 入力値と比較
            match = df_users[(df_users["email"] == l_email.strip()) & 
                             (df_users["password"] == l_pw.strip())]
            
            if not match.empty:
                st.session_state.logged_in = True
                st.session_state.u_email = l_email.strip()
                st.session_state.u_plan = match.iloc[0].get("plan", "free")
                st.rerun()
            else:
                st.error("不一致です。上の『登録状況の確認』で、パスワードが password 列に正しく入っているか確認してください。")
        else:
            st.error("ユーザーデータが読み込めません。")

# 制御ロジック
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_ui()
else:
    st.balloons()
    st.success(f"ログイン成功！ {st.session_state.u_email} さん")
    if st.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()
