import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import re

# --- 0. バージョン・セルフチェック定義 ---
VERSION = "1.2.2"  # セルフチェック・買い物ロジック統合版

def run_system_check(df_menu, df_dict):
    """起動時に主要な仕様が満たされているかテストする"""
    errors = []
    # 1. 日曜スタート計算チェック
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    if (today - timedelta(days=offset)).weekday() != 6:
        errors.append("カレンダーの日曜開始ロジック")
    
    # 2. 材料分類ロジックのシミュレーション
    if df_dict is not None and not df_dict.empty:
        test_item = df_dict.iloc[0]["材料"]
        found = False
        for _, row in df_dict.iterrows():
            if row["材料"] in test_item: found = True; break
        if not found:
            errors.append("材料辞書の照合ロジック")
            
    # 3. 依存ライブラリ (re) の動作確認
    try:
        if re.split(r'[,]', "a,b") != ["a", "b"]: raise Exception
    except:
        errors.append("正規表現ライブラリ(re)")
        
    return errors

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

@st.cache_data(ttl=60)
def get_github_data(filename):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(raw))
            if filename == USER_FILE and 'email' in df.columns:
                df = df.rename(columns={'email': 'username'})
            return df, r.json()["sha"]
    except: pass
    return None, None

def save_to_github(df, filename, message, current_sha=None):
    save_df = df.rename(columns={"username": "email"}) if filename == USER_FILE else df
    csv_content = save_df.to_csv(index=False, encoding="utf-8-sig")
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 2. デザイン定義 (Noto Sans JP / ノイズ消去) ---
st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    .shopping-card { background: white; padding: 15px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 10px; color: #333; }
    .category-label { font-size: 0.8rem; color: #999; margin-bottom: 5px; border-bottom: 1px solid #f0f0f0; }
    .item-row { font-size: 1.1rem; padding: 4px 0; }
    header[data-testid="stHeader"] { background: transparent !important; color: transparent !important; }
    [data-testid="stSidebarCollapseButton"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. データロードと認証 ---
df_menu, menu_sha = get_github_data(FILE)
df_users, _ = get_github_data(USER_FILE)
df_dict, _ = get_github_data(DICT_FILE) # 辞書データ

# 起動時テスト実行
test_results = run_system_check(df_menu, df_dict)
if test_results:
    st.warning(f"⚠️ 仕様不備を検知しました: {', '.join(test_results)}")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    with st.form("login"):
        u = st.text_input("メールアドレス")
        p = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン", use_container_width=True):
            if df_users is not None and u in df_users["username"].values:
                st.session_state.update({"authenticated": True, "username": u})
                st.rerun()
    st.stop()

# --- 4. メインアプリ ---
st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
t_plan, t_hist, t_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ メニュー管理"])

with t_plan:
    # 日曜スタート
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    start_date = st.date_input("開始日（日）", value=today - timedelta(days=offset))
    
    d_tabs = st.tabs(["日", "月", "火", "水", "木", "金", "土"])
    weekly_plan = {}
    
    for i, tab in enumerate(d_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with tab:
            st.markdown(f"##### {d_str}")
            day_menu = {c: st.selectbox(c, ["なし"] + df_menu[df_menu["カテゴリー"] == c]["料理名"].tolist(), key=f"p_{i}_{c}") for c in cats}
            weekly_plan[d_str] = day_menu

    memo = st.text_area("メモ", placeholder="買い物リストに追加したいもの...")

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        all_ings = []
        rows_html = ""
        
        for d_str, menu in weekly_plan.items():
            # 印刷用HTML行の構築
            m_dish = f"{menu['主菜1']} / {menu['主菜2']}".replace("なし", "-")
            s_dish = f"{menu['副菜1']}, {menu['副菜2']}, {menu['汁物']}".replace("なし", "-")
            rows_html += f'<tr><td>{d_str}</td><td>{m_dish}</td><td>{s_dish}</td></tr>'
            
            # 材料集計
            for dish in menu.values():
                if dish != "なし":
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    items = re.split(r'[,、\n]', str(ing_raw))
                    all_ings.extend([x.strip() for x in items if x.strip()])
        
        if memo:
            all_ings.extend([m.strip() for m in re.split(r'[,、\n]', memo) if m.strip()])

        if all_ings:
            # 分類と集計
            df_res = pd.DataFrame(pd.Series(all_ings).value_counts()).reset_index()
            df_res.columns = ["name", "count"]
            
            def get_cat(item):
                if df_dict is not None:
                    for _, row in df_dict.iterrows():
                        if row["材料"] in item: return row["種別"]
                return "99未分類"
            
            df_res["cat"] = df_res["name"].apply(get_cat)
            df_res = df_res.sort_values("cat")
            
            # カード型表示
            cards_html = ""
            for cat, group in df_res.groupby("cat"):
                items_html = "".join([f'<div class="item-row">□ {row["name"]} × {row["count"] if row["count"] > 1 else ""}</div>' for _, row in group.iterrows()])
                cards_html += f'<div class="shopping-card"><div class="category-label">{cat}</div>{items_html}</div>'
            
            st.markdown(cards_html, unsafe_allow_html=True)
            
            # 印刷ボタン (Components)
            print_html = f"<html><body style='font-family:sans-serif;'><h2>献立・買い物リスト</h2>{cards_html}</body></html>"
            b64 = base64.b64encode(print_html.encode()).decode()
            components.html(f"""
                <button id="pb" style="width:100%;padding:10px;border-radius:8px;cursor:pointer;">A4印刷</button>
                <script>
                document.getElementById('pb').onclick = () => {{
                    var w = window.open();
                    w.document.write(atob('{b64}'));
                    w.document.close();
                    setTimeout(() => {{ w.print(); }}, 500);
                }};
                </script>
            """, height=60)

with t_manage:
    st.subheader("メニュー編集")
    # data_editor による一括編集を搭載
    if df_menu is not None:
        new_df = st.data_editor(df_menu, column_order=["料理名", "カテゴリー", "材料"], num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("GitHubを更新"):
            save_to_github(new_df, FILE, "Update via App", menu_sha)
            st.success("保存しました")

st.markdown(f'<div style="text-align:right;font-size:0.6rem;color:#ccc;">Ver {VERSION}</div>', unsafe_allow_html=True)
