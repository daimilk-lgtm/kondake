import streamlit as st
import pandas as pd
import requests
import base64
import io

# Secretsからはトークンだけを読み込む
if "GITHUB_TOKEN" not in st.secrets:
    st.error("Secretsに GITHUB_TOKEN が設定されていません。")
    st.stop()

TOKEN = st.secrets["GITHUB_TOKEN"]

# リポジトリの情報はここで直接指定（ミスを防ぐため）
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"

st.title("献だけ：接続テスト（再）")

# GitHubからデータを取得
url = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

try:
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        st.success("✅ ついに成功！GitHubと繋がりました。")
        content = base64.b64decode(res.json()["content"]).decode("utf-8-sig")
        df = pd.read_csv(io.StringIO(content))
        st.write("### 現在のメニューデータ")
        st.dataframe(df)
    else:
        st.error(f"❌ 認証エラー (Code: {res.status_code})")
        st.write("GitHubメッセージ:", res.json().get("message"))
        st.info("トークンの権限（Contents: Read and write）を再度確認してください。")
except Exception as e:
    st.error(f"エラーが発生しました: {e}")
