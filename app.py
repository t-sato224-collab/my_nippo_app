import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- 1. ページ設定 ---
st.set_page_config(page_title="NIPPO Pro - 高機能日報", page_icon="📑", layout="wide")

# --- 2. データベース接続 ---
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase = create_client(url, key)

if "user" not in st.session_state:
    st.session_state.user = None

# デザイン調整
st.markdown("""
    <style>
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
    .edit-panel { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #007bff; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 認証画面
# ---------------------------------------------------------
def auth_screen():
    st.title("🔐 NIPPO Cloud ログイン")
    choice = st.radio("メニュー", ["ログイン", "新規登録"], horizontal=True)
    email = st.text_input("メールアドレス")
    password = st.text_input("パスワード", type="password")
    
    if choice == "新規登録":
        if st.button("アカウント作成"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("確認メールを送信しました。")
            except Exception as e:
                st.error(f"エラー: {e}")
    else:
        if st.button("ログイン"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error("ログイン失敗")

# ---------------------------------------------------------
# メインアプリ画面
# ---------------------------------------------------------
def main_app():
    user = st.session_state.user
    st.sidebar.title("📑 NIPPO Pro")
    st.sidebar.write(f"👤 {user.email}")
    if st.sidebar.button("ログアウト"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    tab1, tab2 = st.tabs(["✨ 新規登録", "🔎 閲覧・編集・削除"])

    # --- TAB 1: 新規登録 ---
    with tab1:
        with st.form("add_form", clear_on_submit=True):
            st.subheader("日報の新規登録")
            c1, c2 = st.columns(2)
            new_date = c1.date_input("日付", value=datetime.now())
            new_name = c1.text_input("担当者名")
            new_loc = c2.text_input("場所")
            new_content = st.text_area("業務内容")
            if st.form_submit_button("保存する"):
                data = {"date": str(new_date), "person": new_name, "location": new_loc, "content": new_content, "user_id": user.id}
                supabase.table("nippo").insert(data).execute()
                st.success("保存しました！")
                st.rerun()

    # --- TAB 2: 閲覧・編集・削除 (UI刷新) ---
    with tab2:
        # 1. 検索フィルタ
        with st.expander("🔍 絞り込み条件", expanded=False):
            f1, f2, f3 = st.columns([1, 1, 2])
            sel_year = f1.selectbox("年", [2024, 2025, 2026], index=1)
            sel_month = f1.select_slider("月", list(range(1, 13)), value=datetime.now().month)
            search_person = f2.text_input("👤 担当者名で検索")
            search_kw = f3.text_input("🔑 内容キーワードでOR検索")

        # 2. データ取得
        target_month = f"{sel_year}-{sel_month:02d}"
        res = supabase.table("nippo").select("*").eq("user_id", user.id).like("date", f"{target_month}%").order("date", desc=True).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            # フィルタ適用
            if search_person:
                df = df[df["person"].str.contains(search_person, na=False)]
            if search_kw:
                patt = "|".join(search_kw.replace("　", " ").split(" "))
                df = df[df["content"].str.contains(patt, na=False)]

            st.write(f"💡 **行をクリックすると下に編集画面が現れます** (全 {len(df)} 件)")

            # --- ここがポイント：選択可能なデータフレーム ---
            # 選択された行のインデックスを取得
            event = st.dataframe(
                df[["date", "person", "location", "content"]].rename(columns={"date":"日付", "person":"担当者", "location":"場所", "content":"内容"}),
                use_container_width=True,
                on_select="rerun", # クリックで再実行
                selection_mode="single_row", # 1行だけ選択
                hide_index=True
            )

            # 選択された行がある場合の処理
            if len(event.selection.rows) > 0:
                selected_idx = event.selection.rows[0]
                selected_data = df.iloc[selected_idx]
                
                st.markdown("---")
                # 編集・削除パネルを表示
                with st.container():
                    st.markdown(f"### 🛠️ 選択中のデータを操作 (日付: {selected_data['date']})")
                    
                    e_col1, e_col2 = st.columns([2, 1])
                    
                    with e_col1:
                        with st.expander("📝 内容を修正する", expanded=True):
                            up_date = st.date_input("修正後の日付", value=datetime.strptime(selected_data['date'], '%Y-%m-%d'))
                            up_name = st.text_input("修正後の担当者", value=selected_data['person'])
                            up_loc = st.text_input("修正後の場所", value=selected_data['location'])
                            up_content = st.text_area("修正後の業務内容", value=selected_data['content'], height=150)
                            
                            if st.button("🚀 更新を適用する"):
                                update_payload = {"date": str(up_date), "person": up_name, "location": up_loc, "content": up_content}
                                supabase.table("nippo").update(update_payload).eq("id", selected_data['id']).execute()
                                st.success("更新に成功しました！")
                                st.rerun()

                    with e_col2:
                        with st.expander("⚠️ 削除する"):
                            st.write("このデータを消去しますか？")
                            if st.button("🗑️ 完全に削除する"):
                                supabase.table("nippo").delete().eq("id", selected_data['id']).execute()
                                st.success("削除完了。")
                                st.rerun()
            
            # CSV出力ボタン（下部に配置）
            csv_data = df[["date", "person", "location", "content"]].to_csv(index=False).encode('utf_8_sig')
            st.download_button("📥 表示中のデータをCSV保存", csv_data, f"nippo_{target_month}.csv", "text/csv")
        else:
            st.info("表示できるデータがありません。")

# 画面表示
if st.session_state.user is None:
    auth_screen()
else:
    main_app()