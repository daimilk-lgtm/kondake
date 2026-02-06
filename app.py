import streamlit as st
import pandas as pd
import requests
import base64
import io

# Secretsから情報を取得
TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["GITHUB_REPO"]
FILE = st.secrets["GITHUB_FILE"]

st.title("献だけ：データ確認")

# GitHubからデータを取得する関数
def get_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
    headers = {"Authorization": f"token {TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()["content"]).decode("utf-8-sig")
        return pd.read_csv(io.StringIO(content))
    else:
        st.error(f"読み込み失敗。エラーコード: {res.status_code}")
        return None

# データの表示
df = get_data()
if df is not None:
    st.success("✅ GitHubのmenu.csvを読み込めました！")
    st.write("現在登録されているメニュー一覧:")
    st.dataframe(df)
