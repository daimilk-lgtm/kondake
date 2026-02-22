import streamlit as st
import json
import re
from github_utils import get_github_content, save_to_github

USERS_FILE = "users.json"

def get_users_data():
    content, sha = get_github_content(USERS_FILE)
    if content: return json.loads(content), sha
    return {}, None

def login_screen():
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    tab_log, tab_reg = st.tabs(["ログイン", "新規ユーザー登録"])
    
    with tab_log:
        with st.form("login_form"):
            e = st.text_input("メールアドレス")
            p = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン", use_container_width=True):
                users, _ = get_users_data()
                if e in users and users[e] == p:
                    st.session_state['authenticated'] = True
                    st.session_state['user_email'] = e
                    st.rerun()
                else: st.error("認証に失敗しました")
    
    with tab_reg:
        with st.fimport streamlit as st
import json
import re
from github_utils import get_github_content, save_to_github

USERS_FILE = "users.json"

def get_users_data():
    content, sha = get_github_content(USERS_FILE)
    if content: return json.loads(content), sha
    return {}, None

def login_screen():
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    tab_log, tab_reg = st.tabs(["ログイン", "新規ユーザー登録"])
    
    with tab_log:
        with st.form("login_form"):
            e = st.text_input("メールアドレス")
            p = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン", use_container_width=True):
                users, _ = get_users_data()
                if e in users and users[e] == p:
                    st.session_state['authenticated'] = True
                    st.session_state['user_email'] = e
                    st.rerun()
                else: st.error("認証に失敗しました")
    
    with tab_reg:
        with st.form("reg_form"):
            ne = st.text_input("メールアドレス")
            np = st.text_input("パスワード（半角英数字8文字以上）", type="password")
            cp = st.text_input("確認用パスワード", type="password")
            if st.form_submit_button("登録する", use_container_width=True):
                if not re.match(r'^[a-zA-Z0-9]{8,}$', np): st.error("パスワード条件を満たしていません")
                elif np != cp: st.error("パスワードが一致しません")
                else:
                    users, sha = get_users_data()
                    if ne in users: st.error("登録済みのアドレスです")
                    else:
                        users[ne] = np
                        save_to_github(json.dumps(users, ensure_ascii=False), USERS_FILE, f"Reg: {ne}", sha)
                        st.success("登録完了。ログインしてください。")

def show_auth_header():
    st.markdown(f'''
    <div class="auth-header">
        <span class="user-id">{st.session_state["user_email"]}</span>
    </div>
    ''', unsafe_allow_html=True)
    if st.button("ログアウト", key="lo_btn", type="secondary"):
        st.session_state['authenticated'] = False
        st.session_state['user_email'] = ""
        st.rerun()orm("reg_form"):
            ne = st.text_input("メールアドレス")
            np = st.text_input("パスワード（半角英数字8文字以上）", type="password")
            cp = st.text_input("確認用パスワード", type="password")
            if st.form_submit_button("登録する", use_container_width=True):
                if not re.match(r'^[a-zA-Z0-9]{8,}$', np): st.error("パスワード条件を満たしていません")
                elif np != cp: st.error("パスワードが一致しません")
                else:
                    users, sha = get_users_data()
                    if ne in users: st.error("登録済みのアドレスです")
                    else:
                        users[ne] = np
                        save_to_github(json.dumps(users, ensure_ascii=False), USERS_FILE, f"Reg: {ne}", sha)
                        st.success("登録完了。ログインしてください。")

def show_auth_header():
    st.markdown(f'''
    <div class="auth-header">
        <span class="user-id">{st.session_state["user_email"]}</span>
    </div>
    ''', unsafe_allow_html=True)
    if st.button("ログアウト", key="lo_btn", type="secondary"):
        st.session_state['authenticated'] = False
        st.session_state['user_email'] = ""
        st.rerun()
