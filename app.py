import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- 1. ページ設定・デザイン ---
st.set_page_config(
    page_title="NIPPO Cloud Pro",
    page_icon="📑",
    layout="wide",
)

# --- 2. データベース接続設定 ---
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase = create_client(url, key)

# セッション状態（ログインユーザー）の初期化
if "user" not in st.session_state:
    st.session_state.user = None

# カスタムCSS (ボタンや枠のデザイン)
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; background-color: #007bff; color: white; }
    .stDataFrame { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 認証画面 (ログイン・新規登録)
# ---------------------------------------------------------
def auth_screen():
    st.title("🔐 NIPPO Cloud ログイン")
    st.caption("業務日報管理システムへようこそ")
    
    choice = st.radio("メニューを選択してください", ["ログイン", "新規アカウント作成"], horizontal=True)
    
    with st.container():
        email = st.text_input("メールアドレス")
        password = st.text_input("パスワード", type="password")
        
        if choice == "新規アカウント作成":
            st.info("※登録後、届いた確認メールのリンクをクリックしてからログインしてください。")
            if st.button("アカウントを登録する"):
                try:
                    supabase.auth.sign_up({"email": email, "password": password})
                    st.success("確認メールを送信しました。メール内リンクをクリックして承認してください。")
                except Exception as e:
                    st.error(f"登録エラー: {e}")
                    
        else: # ログイン
            if st.button("ログイン"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.success("ログイン成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"ログイン失敗: メールアドレスまたはパスワードが正しくありません。")

# ---------------------------------------------------------
# メインアプリ画面 (ログイン後)
# ---------------------------------------------------------
def main_app():
    user = st.session_state.user
    
    # サイドバー
    st.sidebar.title("👤 ユーザー情報")
    st.sidebar.write(f"ログイン中: \n{user.email}")
    if st.sidebar.button("ログアウト"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    st.title("📑 職務日報システム Pro")
    
    # タブ切り替え
    tab1, tab2 = st.tabs(["✨ 日報を登録する", "🔍 履歴の確認・検索・編集"])

    # --- TAB 1: 新規登録 ---
    with tab1:
        st.subheader("今日の日報入力")
        with st.form("input_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_date = st.date_input("📅 日付", value=datetime.now())
                new_name = st.text_input("👤 担当者名")
            with col2:
                new_loc = st.text_input("📍 場所 (現場名など)")
            
            new_content = st.text_area("📝 業務内容", height=150)
            
            submitted = st.form_submit_button("データベースに保存する")
            
            if submitted:
                if new_name == "" or new_content == "":
                    st.error("担当者名と業務内容は入力必須です。")
                else:
                    data = {
                        "date": str(new_date),
                        "person": new_name,
                        "location": new_loc,
                        "content": new_content,
                        "user_id": user.id  # ログインユーザーのIDを紐付け
                    }
                    try:
                        supabase.table("nippo").insert(data).execute()
                        st.success("✅ 保存が完了しました！")
                        st.balloons()
                    except Exception as e:
                        st.error(f"保存エラー: {e}")

    # --- TAB 2: 履歴の確認・検索・編集・削除 ---
    with tab2:
        st.subheader("データ管理パネル")
        
        # 1. 検索フィルタ
        with st.expander("🔎 絞り込み条件の設定", expanded=False):
            f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
            with f_col1:
                sel_year = st.selectbox("対象年", [2024, 2025, 2026], index=1)
                sel_month = st.select_slider("対象月", options=list(range(1, 13)), value=datetime.now().month)
            with f_col2:
                search_date = st.text_input("📅 特定日検索 (YYYY-MM-DD)")
            with f_col3:
                search_keywords = st.text_input("🔑 内容キーワード検索 (スペース区切りでOR検索)")

        # 2. データ取得 (自分のIDに紐づく、選択した月のデータ)
        target_month = f"{sel_year}-{sel_month:02d}"
        try:
            res = supabase.table("nippo").select("*").eq("user_id", user.id).like("date", f"{target_month}%").order("date", desc=True).execute()
            
            if res.data:
                df = pd.DataFrame(res.data)
                
                # キーワード検索フィルタ
                if search_date:
                    df = df[df["date"] == search_date]
                if search_keywords:
                    keywords = search_keywords.replace("　", " ").split(" ")
                    pattern = "|".join(keywords)
                    df = df[df["content"].str.contains(pattern, case=False, na=False)]

                # 統計
                st.write(f"検索結果: {len(df)} 件")
                
                # 表示用整理
                display_df = df[["date", "person", "location", "content"]].copy()
                display_df.columns = ["日付", "担当者", "場所", "業務内容"]
                st.dataframe(display_df, use_container_width=True)
                
                # CSVダウンロード
                csv = display_df.to_csv(index=False).encode('utf_8_sig')
                st.download_button("📥 結果をCSV保存", csv, f"nippo_{target_month}.csv", "text/csv")

                st.divider()

                # 3. 修正・削除機能
                st.write("🔧 **データの修正・削除**")
                df['select_key'] = df['date'] + " / " + df['location'] + " / " + df['content'].str[:10] + "..."
                target_key = st.selectbox("操作するデータを選んでください", df['select_key'])
                
                # 選択された行の特定
                target_row = df[df['select_key'] == target_key].iloc[0]
                t_id = target_row['id']

                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    with st.expander("📝 修正する"):
                        e_date = st.date_input("修正後の日付", value=datetime.strptime(target_row['date'], '%Y-%m-%d'))
                        e_name = st.text_input("修正後の担当者", value=target_row['person'])
                        e_loc = st.text_input("修正後の場所", value=target_row['location'])
                        e_memo = st.text_area("修正後の内容", value=target_row['content'])
                        if st.button("更新を適用する"):
                            u_data = {"date": str(e_date), "person": e_name, "location": e_loc, "content": e_memo}
                            supabase.table("nippo").update(u_data).eq("id", t_id).execute()
                            st.success("更新しました！")
                            st.rerun()

                with edit_col2:
                    with st.expander("🗑️ 削除する"):
                        st.warning("一度削除すると元に戻せません。")
                        if st.button("このデータを完全に削除する"):
                            supabase.table("nippo").delete().eq("id", t_id).execute()
                            st.success("削除完了。")
                            st.rerun()
            else:
                st.info(f"{target_month} のデータはまだありません。")
        except Exception as e:
            st.error(f"データ取得エラー: {e}")

# ---------------------------------------------------------
# 画面制御 (メイン)
# ---------------------------------------------------------
if st.session_state.user is None:
    auth_screen()
else:
    main_app()