import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta

# --- 1. 設定 (もしSecretsがダメな時のための予備) ---
REPO = "daimilk-lgtm/kondake"
FILE_PATH = "menu.csv"

# トークンの取得（Secretsになければ画面から入力させる）
token_input = st.secrets.get("GITHUB_TOKEN")
if not token_input:
    token_input = st.sidebar.text_input("GitHubトークンを入力してください", type="password")

if not token_input:
    st.warning("左側のメニューからGitHubトークンを設定してください。")
    st.stop()

# --- 2. データ取得・保存関数 ---
def get_github_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {token_input}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()["content"]).decode("utf-8-sig")
        df = pd.read_csv(io.StringIO(content))
        return df, res.json()["sha"]
    return None, None

def save_to_github(df, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {token_input}"}
    csv_content = df.to_csv(index=False, encoding="utf-8-sig")
    encoded = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    data = {"message": "Update menu", "content": encoded, "sha": sha}
    res = requests.put(url, headers=headers, json=data)
    return res.status_code == 200

# --- 3. メイン画面デザイン ---
st.set_page_config(page_title="献だけ", layout="wide")
st.markdown("<style>h1, h2, h3, p { font-family: 'Noto Sans JP', sans-serif; font-weight: 300; }</style>", unsafe_allow_html=True)
st.title("献だけ")

df_master, current_sha = get_github_data()

if df_master is None:
    st.error(f"GitHubとの接続に失敗しました。トークンの権限（repo）を確認してください。")
    st.stop()

tab1, tab2 = st.tabs(["🗓 献立作成", "⚙️ メニュー管理"])

with tab1:
    today = datetime.now()
    start_date = st.date_input("開始日（日曜日）", value=today - timedelta(days=(today.weekday() + 1) % 7))
    
    st.write("### メニューを選択")
    cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
    selected = {}
    
    # 7日分の入力欄
    cols = st.columns(7)
    for i, col in enumerate(cols):
        day_label = (start_date + timedelta(days=i)).strftime('%m/%d')
        with col:
            st.write(f"**{day_label}**")
            day_menu = {}
            for cat in cats:
                opts = df_master[df_master["カテゴリー"] == cat]["料理名"].tolist()
                day_menu[cat] = st.selectbox(f"{cat}", ["なし"] + opts, key=f"{i}_{cat}")
            selected[day_label] = day_menu

    if st.button("献立を確定（買い物リスト作成）", type="primary"):
        st.write("### 今週の買い物リスト")
        all_ingredients = []
        for day, menus in selected.items():
            for cat, dish in menus.items():
                if dish != "なし":
                    ing = df_master[df_master["料理名"] == dish]["材料"].iloc[0]
                    all_ingredients.extend([x.strip() for x in str(ing).split("、")])
        
        counts = pd.Series(all_ingredients).value_counts()
        for item, count in counts.items():
            st.checkbox(f"{item} ({count})")

with tab2:
    st.write("### 新しいメニューを追加")
    with st.form("add_menu"):
        new_name = st.text_input("料理名")
        new_cat = st.selectbox("カテゴリー", cats)
        new_ing = st.text_area("材料（「、」で区切る）")
        if st.form_submit_button("保存"):
            new_row = pd.DataFrame([[new_name, new_cat, new_ing]], columns=df_master.columns)
            updated_df = pd.concat([df_master, new_row], ignore_index=True)
            if save_to_github(updated_df, current_sha):
                st.success("保存しました！")
                st.rerun()
            else:
                st.error("保存に失敗しました。")
    
    st.write("### 現在のマスターデータ")
    st.dataframe(df_master, use_container_width=True)
