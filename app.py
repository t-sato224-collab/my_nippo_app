import streamlit as st
from supabase import create_client
import pandas as pd

# --- 1. 初期設定 ---
st.set_page_config(page_title="NIPPO Cloud Pro", layout="wide")

url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase = create_client(url, key)

# セッション状態（ログイン管理）の初期化
if "user" not in st.session_state:
    st.session_state.user = None

# --- 2. 認証機能（サインイン・ログイン） ---
def auth_screen():
    st.title("🔐 NIPPO Cloud ログイン")
    choice = st.radio("アクションを選んでください", ["ログイン", "新規会員登録"])
    
    email = st.text_input("メールアドレス")
    password = st.text_input("パスワード", type="password")
    
    if choice == "新規会員登録":
        if st.button("アカウント作成"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.success("登録完了！ログインしてください。")
            except Exception as e:
                st.error(f"登録エラー: {e}")
                
    else: # ログイン
        if st.button("ログイン"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error("ログインに失敗しました。メールアドレスかパスワードが違います。")

# --- 3. メインアプリ画面（ログイン後） ---
def main_app():
    user = st.session_state.user
    st.sidebar.write(f"ログイン中: {user.email}")
    if st.sidebar.button("ログアウト"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    st.title("📑 職務日報システム")
    
    tab1, tab2 = st.tabs(["✨ 新規登録", "🔍 自分の履歴"])

    # --- 新規登録 ---
    with tab1:
        with st.form("nippo_form"):
            date = st.date_input("日付")
            loc = st.text_input("場所")
            memo = st.text_area("業務内容")
            if st.form_submit_button("保存する"):
                data = {
                    "date": str(date),
                    "location": loc,
                    "content": memo,
                    "user_id": user.id  # ログイン中のユーザーIDを保存！
                }
                supabase.table("nippo").insert(data).execute()
                st.success("自分のデータとして保存しました。")

    # --- 履歴表示（自分のみ） ---
    with tab2:
        st.subheader("あなたの過去の日報")
        # ログインしている自分の user_id と一致するものだけを取得
        res = supabase.table("nippo").select("*").eq("user_id", user.id).order("date", desc=True).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            df = df[["date", "location", "content"]]
            df.columns = ["日付", "場所", "業務内容"]
            st.dataframe(df, use_container_width=True)
        else:
            st.write("まだ履歴がありません。")

# --- 4. 画面制御 ---
if st.session_state.user is None:
    auth_screen()
else:
    main_app()