import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# --- 0. 基本情報・設定 ---
VERSION = "1.3.2"
REPO = "daimilk-lgtm/kondake"
USER_FILE = "users.csv"
MENU_FILE = "menu.csv"
HIST_FILE = "history.csv"
DICT_FILE = "ingredients.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 1. GitHub連携関数 ---
def get_github_data(filename, is_user=False):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            content_data = r.json()
            raw = base64.b64decode(content_data["content"]).decode("utf-8-sig")
            
            # ユーザーファイルの場合は「空白区切り」かつ「全て文字列」として読み込む
            if is_user:
                df = pd.read_csv(io.StringIO(raw), sep=r'\s+', engine='python', dtype=str)
            else:
                df = pd.read_csv(io.StringIO(raw))
            
            df.columns = [c.strip() for c in df.columns]
            return df, content_data["sha"]
    except: pass
    return pd.DataFrame(), None

def save_to_github(df, filename, message, current_sha=None, is_user=False):
    # ユーザーファイルはタブ区切り、それ以外はカンマ区切り
    sep = "\t" if is_user else ","
    csv_content = df.to_csv(index=False, encoding="utf-8-sig", sep=sep)
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 2. 認証ロジック ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_ui():
    st.markdown('<h1 style="text-align:center; font-weight:100;">献だけ</h1>', unsafe_allow_html=True)
    tab_login, tab_signup = st.tabs(["ログイン", "新規登録"])
    
    df_users, user_sha = get_github_data(USER_FILE, is_user=True)

    with tab_signup:
        st.subheader("アカウント作成")
        new_email = st.text_input("メールアドレス", key="reg_email")
        new_pw = st.text_input("パスワード", type="password", key="reg_pw")
        if st.button("新規登録を実行", use_container_width=True):
            if new_email and new_pw:
                if not df_users.empty and new_email in df_users["email"].values:
                    st.error("このメールアドレスは既に登録されています。")
                else:
                    new_user = pd.DataFrame([[new_email, new_pw, "free"]], columns=["email", "password", "plan"])
                    updated_users = pd.concat([df_users, new_user], ignore_index=True)
                    if save_to_github(updated_users, USER_FILE, f"Register {new_email}", user_sha, is_user=True) in [200, 201]:
                        st.success("登録完了！ログインしてください。")
                    else: st.error("保存に失敗しました。")
            else: st.warning("入力してください。")

    with tab_login:
        st.subheader("ログイン")
        l_email = st.text_input("メールアドレス", key="log_email")
        l_pw = st.text_input("パスワード", type="password", key="log_pw")
        
        # デバッグ用（不要になったら削除してください）
        with st.expander("デバッグ: 登録データ確認"):
            st.write(df_users)

        if st.button("ログイン", type="primary", use_container_width=True):
            if not df_users.empty:
                # 文字列として前後の空白を除去して比較
                match = df_users[(df_users["email"].str.strip() == l_email.strip()) & 
                                 (df_users["password"].str.strip() == l_pw.strip())]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.u_email = l_email.strip()
                    st.session_state.u_plan = match.iloc[0]["plan"]
                    st.rerun()
                else: st.error("IDまたはパスワードが違います。")
            else: st.error("ユーザーデータがありません。")

# --- 3. メインアプリロジック ---
if not st.session_state.logged_in:
    login_ui()
else:
    # --- サイドバー管理 ---
    st.sidebar.title("メニュー")
    st.sidebar.write(f"👤 {st.session_state.u_email}")
    st.sidebar.write(f"権限: {st.session_state.u_plan}")
    if st.sidebar.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()

    # 無料ユーザー向けの広告表示
    if st.session_state.u_plan == "free":
        st.sidebar.markdown("---")
        st.sidebar.info("📢 プレミアムプランなら広告が非表示になります")
        st.warning("【PR】今週の特売：鶏むね肉が安い！")

    # --- アプリ本体 ---
    st.title("献立・買い物リスト")
    
    df_menu, menu_sha = get_github_data(MENU_FILE)
    df_dict, _ = get_github_data(DICT_FILE)
    df_hist, hist_sha = get_github_data(HIST_FILE)

    if df_menu.empty:
        st.error("メニューデータの読み込みに失敗しました。")
        st.stop()

    cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
    tab_plan, tab_hist, tab_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ 管理"])

    with tab_plan:
        today = datetime.now()
        offset = (today.weekday() + 1) % 7
        default_sun = today - timedelta(days=offset)
        start_date = st.date_input("開始日（日）", value=default_sun)
        day_labels = ["日", "月", "火", "水", "木", "金", "土"]
        
        days_tabs = st.tabs([f"{day_labels[i]}" for i in range(7)])
        weekly_plan = {}
        for i, day_tab in enumerate(days_tabs):
            target_date = start_date + timedelta(days=i)
            d_str = target_date.strftime("%Y/%m/%d")
            with day_tab:
                st.markdown(f"##### {d_str} ({day_labels[i]})")
                day_menu = {cat: st.selectbox(cat, ["なし"] + df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=f"s_{i}_{cat}") for cat in cats}
                weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i]}

        memo = st.text_area("追加メモ", placeholder="牛乳、卵など...")

        if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
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
                cards_html = "".join([f'<div style="background:white;padding:10px;border-radius:8px;border:1px solid #eee;margin-bottom:8px;"><div style="font-size:0.7rem;color:#999;">{c}</div>' + "".join([f'<div>□ {r["name"]}</div>' for _, r in g.iterrows()]) + '</div>' for c, g in df_res.groupby("cat")])
                
                st.markdown("### 🛒 買い物リスト")
                st.markdown(cards_html, unsafe_allow_html=True)

                # 改良版印刷ボタン
                raw_html = f"<html><body style='font-family:sans-serif;padding:20px;'><h2>🗓 献立</h2><table style='width:100%;border-collapse:collapse;' border='1'><tr><th>日付</th><th>主菜</th><th>副菜・他</th></tr>{rows_html}</table><h2>🛒 買い物リスト</h2>{cards_html}</body></html>"
                b64_html = base64.b64encode(raw_html.encode('utf-8')).decode('utf-8')
                components.html(f"""<button id='pb' style='width:100%;padding:12px;background:#262730;color:white;border:none;border-radius:8px;cursor:pointer;'>A4印刷 / PDF保存</button>
                    <script>document.getElementById('pb').onclick=function(){{var w=window.open('','_blank');w.document.write(atob('{b64_html}'));w.document.close();setTimeout(function(){{w.focus();w.print();}},500);}}</script>""", height=60)

    # --- 履歴・管理タブは以前と同様 ---
    with tab_hist:
        st.dataframe(df_hist.sort_values("日付", ascending=False), use_container_width=True, hide_index=True)
    
    with tab_manage:
        st.subheader("メニュー登録")
        with st.form("add_form"):
            n = st.text_input("料理名")
            c = st.selectbox("カテゴリー", cats)
            m = st.text_area("材料（カンマ区切り）")
            if st.form_submit_button("新規保存"):
                if n and m:
                    new_df = pd.concat([df_menu, pd.DataFrame([[n, c, m]], columns=df_menu.columns)], ignore_index=True)
                    save_to_github(new_df, MENU_FILE, f"Add {n}", menu_sha)
                    st.cache_data.clear()
                    st.rerun()

    st.markdown(f'<div style="text-align:right;color:#ddd;font-size:0.6rem;">Ver {VERSION}</div>', unsafe_allow_html=True)
