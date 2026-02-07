import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# --- 0. 基本設定・環境 ---
VERSION = "1.3.6"
REPO = "daimilk-lgtm/kondake"
USER_FILE = "users.csv"
MENU_FILE = "menu.csv"
HIST_FILE = "history.csv"
DICT_FILE = "ingredients.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 1. GitHub API 連携層 ---
def get_github_data(filename, is_user=False):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            if is_user:
                df = pd.read_csv(io.StringIO(raw), sep=r'\s+', engine='python', dtype=str)
            else:
                df = pd.read_csv(io.StringIO(raw))
            df.columns = [c.strip() for c in df.columns]
            return df, r.json()["sha"]
    except: pass
    return pd.DataFrame(), None

def save_to_github(df, filename, message, current_sha=None, is_user=False):
    sep = "\t" if is_user else ","
    csv_content = df.to_csv(index=False, encoding="utf-8-sig", sep=sep)
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64, "sha": current_sha} if current_sha else {"message": message, "content": content_b64}
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 2. 認証・ログインUI ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_ui():
    st.markdown("<h1 style='text-align:center; font-weight:100; font-size: 3rem; margin-bottom: 0;'>献だけ</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#999; margin-bottom: 2rem;'>Meal Planning & Shopping List</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        tab_l, tab_s = st.tabs(["ログイン", "新規登録"])
        df_users, user_sha = get_github_data(USER_FILE, is_user=True)
        
        with tab_l:
            l_email = st.text_input("メールアドレス")
            l_pw = st.text_input("パスワード", type="password")
            if st.button("ログイン", type="primary", use_container_width=True):
                df_users = df_users.astype(str).apply(lambda x: x.str.strip())
                match = df_users[(df_users["email"] == l_email.strip()) & (df_users["password"] == l_pw.strip())]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.u_email = l_email.strip()
                    st.session_state.u_plan = match.iloc[0]["plan"]
                    st.rerun()
                else: st.error("ログイン情報が正しくありません")

        with tab_s:
            n_email = st.text_input("登録用アドレス")
            n_pw = st.text_input("設定用パスワード", type="password")
            if st.button("アカウントを作成する", use_container_width=True):
                if n_email and n_pw:
                    new_df = pd.concat([df_users, pd.DataFrame([[n_email, n_pw, "free"]], columns=["email", "password", "plan"])], ignore_index=True)
                    if save_to_github(new_df, USER_FILE, f"New user {n_email}", user_sha, is_user=True) in [200, 201]:
                        st.success("登録が完了しました。")
                    else: st.error("保存エラーが発生しました。")

# --- 3. メインアプリUI ---
if not st.session_state.logged_in:
    login_ui()
else:
    # --- サイドバー (Account & Plan) ---
    with st.sidebar:
        st.markdown(f"### 👤 Account")
        st.write(f"**{st.session_state.u_email}**")
        st.caption(f"Status: {st.session_state.u_plan.upper()}")
        
        if st.button("ログアウト", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
            
        if st.session_state.u_plan == "free":
            st.markdown("---")
            st.markdown("<div style='background:#f9f9f9; padding:1rem; border-radius:5px; border-left: 3px solid #ccc; font-size:0.8rem;'>【広告】プレミアムプランなら広告を非表示にして買い物リストの履歴保存が無制限に！</div>", unsafe_allow_html=True)

    # --- メインエリア (Tabs Navigation) ---
    st.markdown("<h2 style='font-weight:300;'>献立作成</h2>", unsafe_allow_html=True)
    
    df_menu, _ = get_github_data(MENU_FILE)
    df_dict, _ = get_github_data(DICT_FILE)
    df_hist, _ = get_github_data(HIST_FILE)

    # 日曜始まりの仕様
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("週の開始日（日）を選択", value=default_sun)

    # 仕様：7日間のタブ形式
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
    days_tabs = st.tabs([f"{day_labels[i]}" for i in range(7)])
    weekly_plan = {}

    for i, day_tab in enumerate(days_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with day_tab:
            st.markdown(f"<p style='color:#666; font-size:0.9rem;'>{d_str} ({day_labels[i]})</p>", unsafe_allow_html=True)
            day_menu = {}
            # デザイン仕様：標準フォントのラベル
            for cat in cats:
                day_menu[cat] = st.selectbox(cat, ["なし"] + df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=f"sel_{i}_{cat}")
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i]}

    st.markdown("---")
    memo = st.text_area("追加の買い物メモ (牛乳、パンなど)", placeholder="例: 醤油、ビール、トイレットペーパー")

    if st.button("🚀 買い物リストと印刷用ページを生成", type="primary", use_container_width=True):
        # ロジックの実行
        all_ings = []
        rows_html = ""
        for d_str, data in weekly_plan.items():
            v, w = data["menu"], data["weekday"]
            m_dish = f"{v.get('主菜1','-')} / {v.get('主菜2','-')}".replace("なし", "-")
            s_dish = f"{v.get('副菜1','-')}, {v.get('副菜2','-')}, {v.get('汁物','-')}".replace("なし", "-")
            rows_html += f'<tr><td>{d_str}({w})</td><td>{m_dish}</td><td>{s_dish}</td></tr>'
            for dish in v.values():
                if dish != "なし":
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    all_ings.extend([x.strip() for x in str(ing_raw).replace("、", ",").split(",") if x.strip()])
        
        if memo:
            all_ings.extend([x.strip() for x in memo.replace("\n", ",").split(",") if x.strip()])
            
        if all_ings:
            counts = pd.Series(all_ings).value_counts()
            res_list = []
            for item, count in counts.items():
                cat = "99未分類"
                if not df_dict.empty:
                    for _, r in df_dict.iterrows():
                        if r["材料"] in item: cat = r["種別"]; break
                res_list.append({"name": f"{item} × {count}" if count > 1 else item, "cat": cat})
            
            df_res = pd.DataFrame(res_list).sort_values("cat")
            
            # デザイン仕様：カード型買い物リスト
            cards_html = "".join([f'<div style="background:#fff; padding:12px; border:1px solid #ddd; border-radius:8px; margin-bottom:10px;"><strong style="font-size:0.75rem; color:#888;">{c}</strong>' + "".join([f'<div style="font-size:1rem; padding-top:4px;">□ {r["name"]}</div>' for _, r in g.iterrows()]) + '</div>' for c, g in df_res.groupby("cat")])
            
            st.markdown("### 🛒 Shopping List")
            st.markdown(cards_html, unsafe_allow_html=True)
            
            # 印刷用HTML
            raw_html = f"<html><body style='font-family:sans-serif; padding:30px;'><h2>🗓 Weekly Menu</h2><table style='width:100%; border-collapse:collapse;' border='1'><tr><th>Date</th><th>Main</th><th>Side/Soup</th></tr>{rows_html}</table><h2>🛒 Shopping List</h2>{cards_html}</body></html>"
            b64_html = base64.b64encode(raw_html.encode('utf-8')).decode('utf-8')
            components.html(f"""
                <button id='pb' style='width:100%; padding:15px; background:#111; color:#fff; border:none; border-radius:5px; cursor:pointer;'>A4印刷 / PDF保存</button>
                <script>
                document.getElementById('pb').onclick=function(){{
                    var w=window.open('','_blank');
                    w.document.write(atob('{b64_html}'));
                    w.document.close();
                    setTimeout(function(){{ w.print(); }}, 500);
                }}
                </script>""", height=80)

    st.markdown(f"<div style='text-align:right; color:#eee; font-size:0.6rem; padding-top:2rem;'>ver {VERSION}</div>", unsafe_allow_html=True)
