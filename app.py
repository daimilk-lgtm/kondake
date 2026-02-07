import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import hashlib

# --- 0. バージョン管理情報 ---
VERSION = "1.4.3" 

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 2. デザイン定義 (余計な文字を消しつつ、ログアウトボタンを整える) ---
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
    /* アイコン化け対策 */
    .st-emotion-cache-6q9sum.edgvb6w4::before { display: none !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. 認証・GitHub通信関数 ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def get_github_file(filename):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(raw))
            if filename == USER_FILE and "username" not in df.columns:
                return pd.DataFrame(columns=["username", "password"]), r.json()["sha"]
            return df, r.json()["sha"]
    except: pass
    if filename == USER_FILE:
        return pd.DataFrame(columns=["username", "password"]), None
    return None, None

def save_to_github(df, filename, message, current_sha=None):
    csv_content = df.to_csv(index=False, encoding="utf-8-sig")
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 4. 認証フロー ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    auth_tab1, auth_tab2 = st.tabs(["ログイン", "新規ユーザー登録"])
    df_users, user_sha = get_github_file(USER_FILE)

    with auth_tab1:
        with st.form("login_form"):
            u_login = st.text_input("ユーザー名")
            p_login = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン", use_container_width=True):
                h_pwd = make_hash(p_login)
                if not df_users.empty and "username" in df_users.columns:
                    match = df_users[(df_users["username"] == u_login) & (df_users["password"] == h_pwd)]
                    if not match.empty:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u_login
                        st.rerun()
                st.error("ログイン失敗")

    with auth_tab2:
        with st.form("reg_form"):
            u_reg = st.text_input("希望ユーザー名")
            p_reg = st.text_input("希望パスワード", type="password")
            if st.form_submit_button("登録実行", use_container_width=True):
                if u_reg and p_reg:
                    if u_reg in df_users["username"].values:
                        st.warning("使用済み")
                    else:
                        new_user = pd.DataFrame([[u_reg, make_hash(p_reg)]], columns=["username", "password"])
                        updated_users = pd.concat([df_users, new_user], ignore_index=True)
                        save_to_github(updated_users, USER_FILE, f"Add {u_reg}", user_sha)
                        st.success("登録完了")
    st.stop()

# --- 5. メインアプリ ---
# ログアウトボタンをサイドバーに配置
with st.sidebar:
    st.write(f"Login: {st.session_state['username']}")
    if st.button("ログアウト", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["username"] = None
        st.rerun()

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

df_menu, menu_sha = get_github_file(FILE)
df_dict, _ = get_github_file(DICT_FILE)
df_hist, hist_sha = get_github_file(HIST_FILE)

if df_menu is None:
    st.error("データエラー")
    st.stop()

cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
tab_plan, tab_hist, tab_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ メニュー管理"])

with tab_plan:
    # 指定仕様の維持
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日）", value=default_sun) # ユーザーに入力させる
    
    day_labels = ["日", "月", "火", "水", "木", "金", "土"] # 日曜スタート
    
    days_tabs = st.tabs([f"{day_labels[i]}" for i in range(7)])
    weekly_plan = {}
    for i, day_tab in enumerate(days_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with day_tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            day_menu = {cat: st.selectbox(cat, ["なし"] + df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=f"s_{i}_{cat}") for cat in cats}
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i]}

    memo = st.text_area("メモ", placeholder="買い物リストに追加...")

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        # (買い物リスト生成ロジック：以前と全く同じため中略なしで継続)
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
            # (以下、印刷用コンポーネント等も維持)
