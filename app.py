import streamlit as st

st.title("献だけ：接続テスト")
st.write("Secretsの読み込みテスト...")

# Secretsが正しく読み込めているか確認
if "GITHUB_TOKEN" in st.secrets:
    st.success("✅ 設定（Secrets）の読み込みに成功しました！")
else:
    st.error("❌ まだ設定が読み込めていません。")
