if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        new_history_entries = []
        all_ings_list = []
        rows_html = ""
        
        for d_str, data in weekly_plan.items():
            v = data["menu"]
            w_str = data["weekday"]
            
            # --- 1. 表示・印刷用HTMLの構築 ---
            m_dish = f"{v.get('主菜1','-')} / {v.get('主菜2','-')}".replace("なし", "-")
            s_dish = f"{v.get('副菜1','-')}, {v.get('副菜2','-')}, {v.get('汁物','-')}".replace("なし", "-")
            rows_html += f'<tr><td>{d_str}({w_str})</td><td>{m_dish}</td><td>{s_dish}</td></tr>'
            
            # --- 2. 材料の抽出ロジック ---
            day_dishes = []
            for cat in cats:
                dish = v.get(cat, "なし")
                if dish != "なし":
                    day_dishes.append(dish)
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    items = str(ing_raw).replace("、", ",").split(",")
                    all_ings_list.extend([x.strip() for x in items if x.strip()])
            
            # --- 3. 履歴用データの蓄積 ---
            if day_dishes:
                new_history_entries.append({
                    "日付": d_str,
                    "曜日": w_str,
                    "料理名": " / ".join(day_dishes)
                })

        # メモの追加
        if memo:
            memo_items = memo.replace("、", ",").replace("\n", ",").split(",")
            for m_item in memo_items:
                if m_item.strip(): all_ings_list.append(f"{m_item.strip()} (メモ)")

        # 買い物リスト表示（既存のロジック）
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

            # --- 4. GitHubへ履歴を保存 ---
            if new_history_entries:
                new_hist_df = pd.concat([df_hist, pd.DataFrame(new_history_entries)], ignore_index=True)
                # 同じ日付があれば最新で上書き
                new_hist_df = new_hist_df.drop_duplicates(subset=['日付'], keep='last')
                save_to_github(new_hist_df, HIST_FILE, f"Update History {d_str}", hist_sha)
                st.toast("履歴を更新しました！", icon="✅")

            # --- 5. 印刷用コンポーネント（既存通り） ---
            # ... (以下、components.html のコード) ...
