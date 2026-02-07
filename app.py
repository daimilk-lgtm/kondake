import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import re

# --- 0. バージョン・セルフチェック ---
VERSION = "1.2.3" # 履歴・編集ロジック完全復旧版

def run_system_check(df_menu, df_hist):
    errors = []
    # 履歴データの構造チェック
    if df_hist is not None and not df_hist.empty:
        if "日付" not in df_hist.columns:
            errors.append("履歴データの列構成不備")
    # メニューデータの存在チェック
    if df_menu is None or df_menu.empty:
        errors.append("メニューデータの読み込み失敗")
    return errors

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

@st.cache_data(ttl=60)
def get_github_data(filename):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            return pd.read_csv(io.StringIO(raw)), r.json()["sha"]
    except: pass
    return pd.DataFrame(), None

def save_to_github(df, filename, message, current_sha=None):
    csv_content = df.to_csv(index=False, encoding="utf-8-sig")
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 2. デザイン定義 ---
st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    .shopping-card { background: white; padding: 15px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 10px; }
    header[data-testid="stHeader"] { background: transparent !important; color: transparent !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

# データのロード
df_menu, menu_sha = get_github_data(FILE)
df_hist, hist_sha = get_github_data(HIST_FILE)
df_dict, _ = get_github_data(DICT_FILE)

# セルフチェック
test_errors = run_system_check(df_menu, df_hist)
if test_errors:
    st.error(f"🚨 システムチェック未達: {', '.join(test_errors)}")

cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
t_plan, t_hist, t_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ メニュー管理"])

# --- 3. 献立作成タブ ---
with t_plan:
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    start_date = st.date_input("開始日（日）", value=today - timedelta(days=offset))
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    
    d_tabs = st.tabs(day_labels)
    weekly_plan = {}
    for i, tab in enumerate(d_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            day_menu = {cat: st.selectbox(cat, ["なし"] + df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=f"s_{i}_{cat}") for cat in cats}
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i]}

    memo = st.text_area("メモ", placeholder="追加したいもの...")

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        # 材料集計ロジック
        all_ings = []
        for d_str, data in weekly_plan.items():
            for dish in data["menu"].values():
                if dish != "なし":
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    items = re.split(r'[,、\n]', str(ing_raw))
                    all_ings.extend([x.strip() for x in items if x.strip()])
        
        if all_ings:
            st.subheader("🛒 買い物リスト")
            counts = pd.Series(all_ings).value_counts()
            for item, count in counts.items():
                st.checkbox(f"{item} {'(x'+str(count)+')' if count > 1 else ''}", key=f"c_{item}")

# --- 4. 履歴タブ ---
with t_hist:
    st.subheader("過去の履歴")
    if not df_hist.empty:
        # 日付でソートして表示
        st.dataframe(df_hist.sort_values("日付", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("履歴はまだありません。")

# --- 5. メニュー管理タブ (Ver 1.2.1 のロジックを復元) ---
with t_manage:
    st.subheader("⚙️ メニュー管理")
    
    # A. 編集フォーム
    edit_dish = st.selectbox("編集する料理を選んでください", ["選択してください"] + sorted(df_menu["料理名"].tolist()))
    if edit_dish != "選択してください":
        current_data = df_menu[df_menu["料理名"] == edit_dish].iloc[0]
        with st.form("edit_form"):
            new_n = st.text_input("料理名", value=current_data["料理名"])
            c_index = cats.index(current_data["カテゴリー"]) if current_data["カテゴリー"] in cats else 0
            new_c = st.selectbox("カテゴリー", cats, index=c_index)
            new_m = st.text_area("材料", value=current_data["材料"])
            if st.form_submit_button("変更を保存"):
                df_menu.loc[df_menu["料理名"] == edit_dish, ["料理名", "カテゴリー", "材料"]] = [new_n, new_c, new_m]
                save_to_github(df_menu, FILE, f"Update {edit_dish}", menu_sha)
                st.success("更新しました")
                st.rerun()

    st.divider()
    
    # B. 新規追加フォーム
    with st.form("add_form"):
        st.markdown("##### 新規メニューの追加")
        n = st.text_input("料理名")
        c = st.selectbox("カテゴリー", cats)
        m = st.text_area("材料")
        if st.form_submit_button("新規保存"):
            if n and m:
                new_row = pd.DataFrame([[n, c, m]], columns=df_menu.columns)
                df_menu = pd.concat([df_menu, new_row], ignore_index=True)
                save_to_github(df_menu, FILE, f"Add {n}", menu_sha)
                st.success(f"{n} を追加しました")
                st.rerun()

st.markdown(f'<div style="text-align:right;font-size:0.6rem;color:#ccc;">Ver {VERSION}</div>', unsafe_allow_html=True)
