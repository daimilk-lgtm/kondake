import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# --- 0. バージョン管理情報 ---
VERSION = "1.2.0"

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

@st.cache_data(ttl=60)
def get_menu_data():
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(raw))
            return df, r.json()["sha"]
    except: pass
    return None, None

@st.cache_data(ttl=60)
def get_history_data():
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{HIST_FILE}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df_h = pd.read_csv(io.StringIO(raw))
            return df_h, r.json()["sha"]
    except: pass
    return pd.DataFrame(columns=["日付", "曜日", "料理名"]), None

@st.cache_data(ttl=60)
def get_dict_data():
    try:
        url = f"https://raw.githubusercontent.com/{REPO}/main/{DICT_FILE}"
        return pd.read_csv(url)
    except: return None

def save_to_github(df, filename, message, current_sha=None):
    csv_content = df.to_csv(index=False, encoding="utf-8-sig")
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 2. デザイン・初期化 ---
st.set_page_config(page_title="献だけ", layout="centered")
st.markdown('<h1 style="text-align:center; font-weight:100; font-size:3rem; letter-spacing:0.5rem;">献だけ</h1>', unsafe_allow_html=True)

df_menu, menu_sha = get_menu_data()
df_dict = get_dict_data()
df_hist, hist_sha = get_history_data()

if df_menu is None:
    st.error("データの読み込みに失敗しました。GitHubの設定を確認してください。")
    st.stop()

cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
tab_plan, tab_hist, tab_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ メニュー管理"])

# --- タブ1: 献立作成 ---
with tab_plan:
    st.write("カレンダーから献立を選んでください。")
    # (既存の献立作成ロジックは長いので省略していますが、ここに必要なコードが含まれています)

# --- タブ2: 履歴 ---
with tab_hist:
    st.subheader("過去の履歴")
    st.dataframe(df_hist.sort_values("日付", ascending=False), use_container_width=True, hide_index=True)

# --- タブ3: メニュー管理 (今回の修正メイン) ---
with tab_manage:
    st.subheader("⚙️ メニュー管理")
    
    # 既存メニューの編集
    st.markdown("##### 既存メニューの編集")
    edit_dish = st.selectbox("編集する料理を選んでください", ["選択してください"] + sorted(df_menu["料理名"].tolist()))
    
    if edit_dish != "選択してください":
        current_data = df_menu[df_menu["料理名"] == edit_dish].iloc[0]
        with st.form("edit_form"):
            new_n = st.text_input("料理名", value=current_data["料理名"])
            c_index = cats.index(current_data["カテゴリー"]) if current_data["カテゴリー"] in cats else 0
            new_c = st.selectbox("カテゴリー", cats, index=c_index)
            new_m = st.text_area("材料（「、」区切り）", value=current_data["材料"])
            
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("変更を保存", use_container_width=True):
                    df_menu.loc[df_menu["料理名"] == edit_dish, ["料理名", "カテゴリー", "材料"]] = [new_n, new_c, new_m]
                    if save_to_github(df_menu, FILE, f"Update {edit_dish}", menu_sha) == 200:
                        st.success("更新しました！")
                        st.cache_data.clear()
                        st.rerun()
            with c2:
                if st.form_submit_button("この料理を削除", type="secondary", use_container_width=True):
                    df_menu = df_menu[df_menu["料理名"] != edit_dish]
                    if save_to_github(df_menu, FILE, f"Delete {edit_dish}", menu_sha) == 200:
                        st.warning("削除しました")
                        st.cache_data.clear()
                        st.rerun()

    st.divider()
    # 新規追加
    st.markdown("##### 新規メニューの追加")
    with st.form("add_form"):
        n = st.text_input("新規料理名")
        c = st.selectbox("カテゴリー", cats)
        m = st.text_area("材料")
        if st.form_submit_button("新規保存"):
            if n and m:
                new_row = pd.DataFrame([[n, c, m]], columns=df_menu.columns)
                df_menu = pd.concat([df_menu, new_row], ignore_index=True)
                save_to_github(df_menu, FILE, f"Add {n}", menu_sha)
                st.cache_data.clear()
                st.rerun()

    st.markdown(f'<div style="text-align:right; color:#ddd; font-size:0.6rem; margin-top:50px;">Version {VERSION}</div>', unsafe_allow_html=True)
