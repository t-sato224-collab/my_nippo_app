import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- 1. ページ設定 (デザインの基本) ---
st.set_page_config(
    page_title="NIPPO Cloud - 業務日報システム",
    page_icon="📑",
    layout="wide",
)

# --- 2. 接続設定 ---
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase = create_client(url, key)

# カスタムCSSで少しだけデザインを調整
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stDataFrame { border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 3. メインタイトル ---
st.title("📑 NIPPO Cloud")
st.caption("業務日報の登録・検索・管理システム")

# --- 4. タブ機能による画面分割 ---
tab1, tab2 = st.tabs(["✨ 新規日報登録", "🔍 データ検索・管理"])

# ---------------------------------------------------------
# TAB 1: 新規登録画面
# ---------------------------------------------------------
with tab1:
    st.subheader("日報を作成する")
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_date = st.date_input("📅 日付", value=datetime.now())
            new_name = st.text_input("👤 担当者名", placeholder="氏名を入力")
        with col2:
            new_loc = st.text_input("📍 場所", placeholder="現場名、客先名など")
            
        new_content = st.text_area("📝 業務内容", placeholder="今日行った作業を詳しく記入してください", height=150)
        
        submitted = st.form_submit_button("この内容でデータベースに保存する")
        
        if submitted:
            if new_name == "" or new_content == "":
                st.error("❌ 担当者名と業務内容は必須項目です。")
            else:
                data = {"date": str(new_date), "person": new_name, "location": new_loc, "content": new_content}
                try:
                    supabase.table("nippo").insert(data).execute()
                    st.success("✅ 正常に保存されました！「データ検索」タブから確認できます。")
                    st.balloons()
                except Exception as e:
                    st.error(f"⚠️ 保存エラー: {e}")

# ---------------------------------------------------------
# TAB 2: 検索・管理画面
# ---------------------------------------------------------
with tab2:
    # --- 検索パネル (Expanderでスッキリ) ---
    with st.expander("🔎 検索・フィルタ条件", expanded=True):
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        with col_f1:
            years = [2024, 2025, 2026]
            sel_year = st.selectbox("対象年", years, index=1)
            sel_month = st.select_slider("対象月", options=list(range(1, 13)), value=datetime.now().month)
        with col_f2:
            search_date = st.text_input("📅 特定日検索", placeholder="2025-01-16")
            search_person = st.text_input("👤 担当者検索", placeholder="氏名の一部")
        with col_f3:
            search_keywords = st.text_input("🔑 内容キーワード検索 (スペース区切りでOR検索)", placeholder="例: 打合せ 現場 移動")

    # --- データ取得 ---
    target_month = f"{sel_year}-{sel_month:02d}"
    
    try:
        # 月別データ取得
        res = supabase.table("nippo").select("*").like("date", f"{target_month}%").order("date", desc=True).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            
            # --- フィルタリング処理 ---
            if search_date:
                df = df[df["date"] == search_date]
            if search_person:
                df = df[df["person"].str.contains(search_person, case=False, na=False)]
            if search_keywords:
                keywords = search_keywords.replace("　", " ").split(" ")
                pattern = "|".join(keywords)
                df = df[df["content"].str.contains(pattern, case=False, na=False)]

            # --- 統計情報の表示 ---
            m1, m2, m3 = st.columns(3)
            m1.metric("総件数", f"{len(df)} 件")
            m2.metric("今月の稼働日数", f"{df['date'].nunique()} 日")
            m3.metric("アクティブ担当者", f"{df['person'].nunique()} 名")

            # --- 表の表示 ---
            display_df = df[["date", "person", "location", "content"]]
            display_df.columns = ["日付", "担当者", "場所", "業務内容"]
            
            st.dataframe(
                display_df, 
                use_container_width=True,
                column_config={
                    "日付": st.column_config.TextColumn("📅 日付"),
                    "担当者": st.column_config.TextColumn("👤 担当者"),
                    "場所": st.column_config.TextColumn("📍 場所"),
                    "業務内容": st.column_config.TextColumn("📝 業務内容"),
                }
            )
            
            # --- アクションボタン (CSV) ---
            st.download_button(
                label="📥 絞り込み結果をCSVでダウンロード",
                data=display_df.to_csv(index=False).encode('utf_8_sig'),
                file_name=f"report_{target_month}.csv",
                mime="text/csv",
            )
        else:
            st.info(f"💡 {target_month} のデータはまだ登録されていません。")
            
    except Exception as e:
        st.error(f"🚨 データ取得エラー: {e}")

# --- フッター ---
st.divider()
st.caption("© 2025 NIPPO Cloud System - Your Personal Business Productivity Tool")