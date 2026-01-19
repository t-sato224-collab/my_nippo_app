import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- 1. ページ設定 ---
st.set_page_config(page_title="NIPPO Pro", page_icon="📑", layout="wide")

# --- 2. 接続 ---
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase = create_client(url, key)

if "user" not in st.session_state:
    st.session_state.user = None

# --- 認証画面 ---
def auth_screen():
    st.title("🔐 ログイン")
    choice = st.radio("メニュー", ["ログイン", "新規登録"], horizontal=True)
    email = st.text_input("メールアドレス")
    password = st.text_input("パスワード", type="password")
    if st.button("実行"):
        try:
            if choice == "新規登録":
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("確認メールを送りました。")
            else:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
        except Exception as e:
            st.error(f"エラー: {e}")

# --- メインアプリ ---
def main_app():
    user = st.session_state.user
    st.sidebar.write(f"👤 {user.email}")
    if st.sidebar.button("ログアウト"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    tab1, tab2 = st.tabs(["✨ 登録", "🔎 閲覧・編集・削除"])

    with tab1:
        with st.form("add"):
            st.subheader("日報登録")
            d = st.date_input("日付")
            n = st.text_input("担当者")
            l = st.text_input("場所")
            c = st.text_area("内容")
            if st.form_submit_button("保存"):
                supabase.table("nippo").insert({"date":str(d),"person":n,"location":l,"content":c,"user_id":user.id}).execute()
                st.success("保存完了")
                st.rerun()

    with tab2:
        # フィルタ
        f_col = st.columns([1, 1, 2])
        y = f_col[0].selectbox("年", [2024, 2025, 2026], index=1)
        m = f_col[0].select_slider("月", list(range(1,13)), value=datetime.now().month)
        
        # データ取得
        res = supabase.table("nippo").select("*").eq("user_id", user.id).like("date", f"{y}-{m:02d}%").order("date", desc=True).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            
            st.info("💡 行をクリックして選択すると、下に編集画面が出ます。")
            
            # --- 選択機能付きデータフレーム ---
            # ここでエラーが出る場合は、requirements.txtでstreamlitのバージョンが1.35.0以上になっているか確認してください
            event = st.dataframe(
                df[["date", "person", "location", "content"]].rename(columns={"date":"日付","person":"担当者","location":"場所","content":"内容"}),
                use_container_width=True,
                on_select="rerun",
                selection_mode="single_row",
                hide_index=True
            )

            # 選択された行の処理
            # event.selection.rows が存在するかチェック
            if hasattr(event, 'selection') and len(event.selection.rows) > 0:
                row_idx = event.selection.rows[0]
                selected = df.iloc[row_idx]
                
                st.markdown("---")
                st.subheader("🛠️ 選択中のデータを編集")
                
                with st.container(border=True):
                    u_date = st.date_input("修正日", value=datetime.strptime(selected['date'], '%Y-%m-%d'))
                    u_name = st.text_input("修正名", value=selected['person'])
                    u_loc = st.text_input("修正場所", value=selected['location'])
                    u_cont = st.text_area("修正内容", value=selected['content'])
                    
                    c1, c2 = st.columns(2)
                    if c1.button("🚀 更新する"):
                        supabase.table("nippo").update({"date":str(u_date),"person":u_name,"location":u_loc,"content":u_cont}).eq("id", selected['id']).execute()
                        st.success("更新しました")
                        st.rerun()
                    if c2.button("🗑️ 削除する"):
                        supabase.table("nippo").delete().eq("id", selected['id']).execute()
                        st.success("削除しました")
                        st.rerun()

            # ダウンロード
            st.download_button("📥 CSV保存", df.to_csv(index=False).encode('utf-8-sig'), "data.csv", "text/csv")
        else:
            st.write("データなし")

if st.session_state.user is None:
    auth_screen()
else:
    main_app()