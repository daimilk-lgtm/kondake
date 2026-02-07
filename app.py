import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# --- 0. バージョン管理情報 ---
VERSION = "1.3.0"  # ログイン機能追加版

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1234")  # Secretsに設定するかデフォルトを使用

# --- ログインチェック ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
        pwd = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if pwd == APP_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        return False
    return True

# ログインしていない場合はここで止める
if not check_password():
    st.stop()

# --- 2. データ取得・保存関数 (変更なし) ---
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

# --- 3. デザイン定義 (変更なし) ---
st.set_page_config(page_title="献だけ", layout="centered")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    .shopping-card { background: white; padding: 15px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 10px; }
    .category-label { font-size: 0.8rem; color: #999; margin-bottom: 5px; }
    .item-row { font-size: 1.1rem; padding: 4px 0; border-bottom: 0.5px solid #f9f9f9; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

df_menu, menu_sha = get_menu_data()
df_dict = get_dict_data()
df_hist, hist_sha = get_history_data()

if df_menu is None:
    st.error("データの読み込みに失敗しました。")
    st.stop()

cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
tab_plan, tab_hist, tab_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ メニュー管理"])

with tab_plan:
    # 指定通りの日付入力と日曜スタート設定
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日）", value=default_sun)  # 日付はユーザーに入力させる
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]  # 日曜スタートにする
    
    days_tabs = st.tabs([f"{day_labels[i]}" for i in range(7)])
    weekly_plan = {}
    for i, day_tab in enumerate(days_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with day_tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            day_menu = {cat: st.selectbox(cat, ["なし"] + df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=f"s_{i}_{cat}") for cat in cats}
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i]}

    memo = st.text_area("メモ", placeholder="買い物リストに追加したいもの...")

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        all_ings_list = []
        rows_html = ""
        
        for d_str, data in weekly_plan.items():
            v = data["menu"]
            w_str = data["weekday"]
            m_dish = f"{v.get('主菜1','-')} / {v.get('主菜2','-')}".replace("なし", "-")
            s_dish = f"{v.get('副菜1','-')}, {v.get('副菜2','-')}, {v.get('汁物','-')}".replace("なし", "-")
            rows_html += f'<tr><td>{d_str}({w_str})</td><td>{m_dish}</td><td>{s_dish}</td></tr>'
            for dish in v.values():
                if dish != "なし":
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    items = str(ing_raw).replace("、", ",").split(",")
                    all_ings_list.extend([x.strip() for x in items if x.strip()])

        if memo:
            memo_items = memo.replace("、", ",").replace("\n", ",").split(",")
            all_ings_list.extend([m.strip() for m in memo_items if m.strip()])

        if all_ings_list:
            counts = pd.Series(all_ings_list).value_counts()
            result_data = []
            for item, count in counts.items():
                category = "99未分類"
                if df_dict is not None:
                    for _, row in df_dict.iterrows():
                        if row["材料"] in item: category = row["種別"]; break
                result_data.append({"name": f"{item} × {count}" if count > 1 else item, "cat": category})
            
            df_res = pd.DataFrame(result_data).sort_values("cat")
            cards_html = "".join([f'<div class="shopping-card"><div class="category-label">{cat}</div>' + "".join([f'<div class="item-row">□ {row["name"]}</div>' for _, row in group.iterrows()]) + '</div>' for cat, group in df_res.groupby("cat")])
            
            st.markdown("### 🛒 買い物リスト")
            st.markdown(cards_html, unsafe_allow_html=True)

            raw_html = f"<html><body style='font-family:sans-serif;padding:20px;'><h2>🗓 献立</h2><table style='width:100%;border-collapse:collapse;margin-bottom:20px;' border='1'><tr><th>日付</th><th>主菜</th><th>副菜・汁物</th></tr>{rows_html}</table><h2>🛒 買い物リスト</h2>{cards_html}</body></html>"
            b64_html = base64.b64encode(raw_html.encode('utf-8')).decode('utf-8')

            components.html(f"""
                <div style="margin-top:20px;"><button id="pbtn" style="width: 100%; background-color: #262730; color: white; padding: 12px; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem;">A4印刷する</button></div>
                <script>
                document.getElementById('pbtn').onclick = function() {{
                    var w = window.open('', '_blank');
                    w.document.write(decodeURIComponent(escape(atob('{b64_html}'))));
                    w.document.close();
                    setTimeout(function() {{ w.focus(); w.print(); }}, 500);
                }};
                </script>""", height=80)

# --- 履歴・管理タブは以前のロジックのまま維持 ---
with tab_hist:
    st.subheader("過去の履歴")
    if not df_hist.empty:
        st.dataframe(df_hist.sort_values("日付", ascending=False), use_container_width=True, hide_index=True)

with tab_manage:
    st.subheader("⚙️ メニュー管理")
    edit_dish = st.selectbox("編集する料理を選んでください", ["選択してください"] + sorted(df_menu["料理名"].tolist()))
    if edit_dish != "選択してください":
        current_data = df_menu[df_menu["料理名"] == edit_dish].iloc[0]
        with st.form("edit_form"):
            new_n = st.text_input("料理名", value=current_data["料理名"])
            c_val = current_data["カテゴリー"]
            new_c = st.selectbox("カテゴリー", cats, index=cats.index(c_val) if c_val in cats else 0)
            new_m = st.text_area("材料", value=current_data["材料"])
            if st.form_submit_button("変更を保存"):
                df_menu.loc[df_menu["料理名"] == edit_dish, ["料理名", "カテゴリー", "材料"]] = [new_n, new_c, new_m]
                save_to_github(df_menu, FILE, f"Update {edit_dish}", menu_sha)
                st.cache_data.clear()
                st.rerun()

    st.divider()
    with st.form("add_form"):
        st.markdown("##### 新規メニューの追加")
        n = st.text_input("料理名")
        c = st.selectbox("カテゴリー", cats)
        m = st.text_area("材料")
        if st.form_submit_button("新規保存"):
            if n and m:
                new_df = pd.concat([df_menu, pd.DataFrame([[n, c, m]], columns=df_menu.columns)], ignore_index=True)
                save_to_github(new_df, FILE, f"Add {n}", menu_sha)
                st.cache_data.clear()
                st.rerun()

    st.markdown(f'<div style="text-align: right; color: #ddd; font-size: 0.6rem; margin-top: 50px;">Version {VERSION}</div>', unsafe_allow_html=True)
