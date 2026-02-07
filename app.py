# --- 0. バージョン管理情報 ---
VERSION = "1.2.0"  # 既存メニューの修正機能を追加

# (中略: 1. 接続設定や 2. デザイン定義はそのまま)
# ※管理を楽にするため、tab_manage の中身だけ重点的に修正します

with tab_manage:
    st.subheader("⚙️ メニュー管理")
    
    # --- 修正・編集機能 ---
    st.markdown("##### 既存メニューの編集")
    edit_dish = st.selectbox("編集する料理を選んでください", ["選択してください"] + df_menu["料理名"].tolist())
    
    if edit_dish != "選択してください":
        # 選んだ料理の現在のデータを取得
        current_data = df_menu[df_menu["料理名"] == edit_dish].iloc[0]
        
        with st.form("edit_form"):
            new_n = st.text_input("料理名", value=current_data["料理名"])
            new_c = st.selectbox("カテゴリー", cats, index=cats.index(current_data["カテゴリー"]))
            new_m = st.text_area("材料（「、」区切り）", value=current_data["材料"])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("変更を保存"):
                    # データを差し替え
                    df_menu.loc[df_menu["料理名"] == edit_dish, ["料理名", "カテゴリー", "材料"]] = [new_n, new_c, new_m]
                    if save_to_github(df_menu, FILE, f"Update {edit_dish}", menu_sha) == 200:
                        st.success(f"{edit_dish} を更新しました！")
                        st.cache_data.clear()
                        st.rerun()
            with col2:
                # ついでに削除ボタンも付けておきます（必要な場合）
                if st.form_submit_button("この料理を削除", type="secondary"):
                    df_menu = df_menu[df_menu["料理名"] != edit_dish]
                    if save_to_github(df_menu, FILE, f"Delete {edit_dish}", menu_sha) == 200:
                        st.warning(f"{edit_dish} を削除しました")
                        st.cache_data.clear()
                        st.rerun()

    st.divider()

    # --- 新規追加機能 (これまでのフォーム) ---
    st.markdown("##### 新規メニューの追加")
    with st.form("add_menu_form", clear_on_submit=True):
        n = st.text_input("料理名")
        c = st.selectbox("カテゴリー", cats)
        m = st.text_area("材料（「、」区切り）")
        if st.form_submit_button("新規保存"):
            if n and m:
                new_df = pd.concat([df_menu, pd.DataFrame([[n, c, m]], columns=df_menu.columns)], ignore_index=True)
                if save_to_github(new_df, FILE, f"Add {n}", menu_sha) == 200:
                    st.cache_data.clear()
                    st.rerun()

    st.divider()
    st.dataframe(df_menu, use_container_width=True)
    st.markdown(f'<div style="text-align: right; color: #ddd; font-size: 0.6rem; margin-top: 50px;">Version {VERSION}</div>', unsafe_allow_html=True)
