# --- (前半のインポートや認証部分はそのまま) ---

# --- メインアプリ画面（修正・削除機能付き） ---
def main_app():
    user = st.session_state.user
    st.sidebar.write(f"ログイン中: {user.email}")
    if st.sidebar.button("ログアウト"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    st.title("📑 職務日報システム Pro")
    
    tab1, tab2 = st.tabs(["✨ 新規登録", "🔍 履歴の確認・編集"])

    # --- 新規登録 ---
    with tab1:
        with st.form("nippo_form", clear_on_submit=True):
            date = st.date_input("日付")
            loc = st.text_input("場所")
            memo = st.text_area("業務内容")
            if st.form_submit_button("保存する"):
                data = {"date": str(date), "location": loc, "content": memo, "user_id": user.id}
                supabase.table("nippo").insert(data).execute()
                st.success("保存しました！")
                st.rerun()

    # --- 履歴表示・編集・削除 ---
    with tab2:
        st.subheader("データ管理")
        res = supabase.table("nippo").select("*").eq("user_id", user.id).order("date", desc=True).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            # 表示用の表
            display_df = df[["date", "location", "content"]].copy()
            display_df.columns = ["日付", "場所", "業務内容"]
            st.dataframe(display_df, use_container_width=True)

            st.divider()
            
            # --- 編集・削除エリア ---
            st.write("🔧 **選択したデータを修正または削除する**")
            # どのデータを操作するか、日付と場所で選択させる
            df['selection_label'] = df['date'] + " - " + df['location']
            target_label = st.selectbox("操作するデータを選択してください", df['selection_label'])
            
            # 選択されたデータの詳細を取得
            target_data = df[df['selection_label'] == target_label].iloc[0]
            target_id = target_data['id']

            edit_col1, edit_col2 = st.columns(2)
            
            with edit_col1:
                # 修正フォーム
                with st.expander("📝 このデータを修正する"):
                    edit_date = st.date_input("修正後の日付", value=datetime.strptime(target_data['date'], '%Y-%m-%d'))
                    edit_loc = st.text_input("修正後の場所", value=target_data['location'])
                    edit_memo = st.text_area("修正後の業務内容", value=target_data['content'])
                    if st.button("更新を保存する"):
                        update_data = {"date": str(edit_date), "location": edit_loc, "content": edit_memo}
                        supabase.table("nippo").update(update_data).eq("id", target_id).execute()
                        st.success("更新完了！")
                        st.rerun()

            with edit_col2:
                # 削除フォーム
                with st.expander("🗑️ このデータを削除する"):
                    st.warning("この操作は取り消せません。")
                    if st.button("本当に削除する"):
                        supabase.table("nippo").delete().eq("id", target_id).execute()
                        st.success("削除しました。")
                        st.rerun()
        else:
            st.write("データがありません。")

# --- (後半の画面制御部分はそのまま) ---