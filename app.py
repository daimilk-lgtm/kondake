import streamlit as st
import pandas as pd
import sqlite3
import requests
import base64
import io
from datetime import datetime, timedelta

# --- 1. GitHub連携設定 ---
TOKEN = st.secrets.get("GITHUB_TOKEN")
REPO = st.secrets.get("GITHUB_REPO")
FILE_PATH = st.secrets.get("GITHUB_FILE", "menu.csv")

@st.cache_data(ttl=60)
def get_csv_from_github():
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
        headers = {"Authorization": f"token {TOKEN}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content = base64.b64decode(res.json()["content"]).decode("utf-8-sig")
            # 読み込み時に列名を強制指定して文字化けによるエラーを防ぐ
            df = pd.read_csv(io.StringIO(content))
            # 列名のスペース除去とクリーンアップ
            df.columns = [c.strip() for c in df.columns]
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            return df, res.json()["sha"]
    except Exception as e:
        st.error(f"読み込み失敗: {e}")
    return pd.DataFrame(), None

def update_github_csv(df, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {TOKEN}"}
    content_base64 = base64.b64encode(df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8")).decode("utf-8")
    data = {"message": "Update menu", "content": content_base64, "sha": sha}
    res = requests.put(url, headers=headers, json=data)
    return res.status_code == 200

# データ取得
df_master, current_sha = get_csv_from_github()
conn = sqlite3.connect(':memory:', check_same_thread=False)
if not df_master.empty:
    df_master.to_sql('menu_table', conn, index=False, if_exists='replace')

# --- 2. デザイン ---
st.set_page_config(page_title="献だけ", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300&display=swap');
    html, body, [class*="css"], p, div, select, input, h2, h3 {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .title-wrapper { text-align: center; padding: 1rem 0; }
    .title-text { font-size: 3rem; font-weight: 100; letter-spacing: 0.5em; color: #333; }
    .thin-title { font-weight: 300 !important; font-size: 1.5rem; margin-top: 2rem; margin-bottom: 1rem; }
    .date-text { text-align: right; font-size: 0.8rem; color: #666; }
</style>
<div class="title-wrapper"><div class="title-text">献だけ</div></div>
""", unsafe_allow_html=True)

today = datetime.now()
st.markdown(f'<div class="date-text">作成日: {today.strftime("%Y/%m/%d")}</div>', unsafe_allow_html=True)

# --- 3. タブ構成 ---
tab_plan, tab_manage = st.tabs(["🗓 献立作成", "⚙️ メニュー管理"])

with tab_plan:
    if not df_master.empty:
        start_date = st.date_input("開始日（日曜日）", value=today - timedelta(days=(today.weekday() + 1) % 7))
        day_names = ["日", "月", "火", "水", "木", "金", "土"]
        day_tabs = st.tabs([f"{day_names[i]} ({(start_date + timedelta(days=i)).strftime('%m/%d')})" for i in range(7)])
        cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
        
        selected_plan = {}
        for i, tab in enumerate(day_tabs):
            with tab:
                cols = st.columns(5)
                day_plan = {}
                d_label = f"{day_names[i]}({(start_date + timedelta(days=i)).strftime('%m/%d')})"
                for j, cat in enumerate(cats):
                    with cols[j]:
                        # SQLクエリで正確に抽出
                        opts = pd.read_sql(f"SELECT 料理名 FROM menu_table WHERE カテゴリー='{cat}'", conn)["料理名"].tolist()
                        val = st.selectbox(cat, ["選択なし"] + opts, key=f"s_{i}_{j}")
                        day_plan[cat] = val
                selected_plan[d_label] = day_plan

        st.divider()
        user_memo = st.text_area("📝 フリーメモ", key="f_memo")
        
        if st.button("こんだけ作成", type="primary", use_container_width=True):
            st.markdown('<div class="thin-title">今週の献立</div>', unsafe_allow_html=True)
            st.table(pd.DataFrame(selected_plan).T)
            st.markdown('<div class="thin-title">買い物リスト</div>', unsafe_allow_html=True)
            if user_memo: st.info(user_memo)
            
            raw_ings = []
            for d in selected_plan.values():
                for dish in d.values():
                    if dish != "選択なし":
                        m = df_master[df_master["料理名"] == dish]
                        if not m.empty:
                            items = str(m["材料"].iloc[0]).replace("、", "\n").replace(",", "\n").splitlines()
                            raw_ings.extend([x.strip() for x in items if x.strip()])
            if raw_ings:
                counts = pd.Series(raw_ings).value_counts().sort_index()
                for n, c in counts.items():
                    st.checkbox(f"{n} × {c}" if c > 1 else n, key=f"c_{n}")
    else:
        st.error("データの読み込みに失敗しました。GitHubのCSVを確認してください。")

with tab_manage:
    st.markdown('<div class="thin-title">メニューの追加</div>', unsafe_allow_html=True)
    with st.form("add_form", clear_on_submit=True):
        n_dish = st.text_input("料理名")
        n_cat = st.selectbox("カテゴリー", ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"])
        n_ing = st.text_area("材料（「、」で区切る）")
        if st.form_submit_button("保存する"):
            if n_dish and n_ing and current_sha:
                new_df = pd.concat([df_master, pd.DataFrame([[n_dish, n_cat, n_ing]], columns=df_master.columns)], ignore_index=True)
                if update_github_csv(new_df, current_sha):
                    st.success("保存完了！")
                    st.cache_data.clear()
                    st.rerun()
                else: st.error("保存失敗")
    st.divider()
    st.dataframe(df_master, use_container_width=True)
