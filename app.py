import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# --- 側邊欄：功能與基本資料 ---
with st.sidebar:
    st.header("👤 基本資料設定")
    # 這裡只留下年齡與性別，名字我們移到中間，確保即時連動
    c_age = st.number_input("投保年齡", value=27)
    c_gender = st.selectbox("性別", ["男", "女"])
    
    st.divider()
    st.header("📂 檔案載入")
    uploaded_file = st.file_uploader("上傳 PDF/圖片/Excel", type=["pdf", "xlsx", "png", "jpg", "jpeg"])
    
    st.divider()
    mode = st.radio("功能切換：", ["1. 資料錄入與對照", "2. 產出理賠診斷報告"])

# --- 初始化表格 ---
if 'current_df' not in st.session_state:
    st.session_state['current_df'] = pd.DataFrame(columns=["險種名稱", "類別", "保費", "預估理賠額(萬)", "期滿(民國)"])

# --- 模式 1：資料錄入 ---
if mode == "1. 資料錄入與對照":
    # 關鍵修正：將姓名輸入框直接放在標題位置
    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        # 使用 st.session_state 儲存名字，以便報告頁面共用
        c_name = st.text_input("請輸入客戶姓名：", value=st.session_state.get('c_name', "新客戶"))
        st.session_state['c_name'] = c_name
    
    # 動態標題
    st.header(f"📝 {c_name} 的保單明細表")
    
    # 編輯區 (表格最大化)
    edited_df = st.data_editor(
        st.session_state['current_df'],
        num_rows="dynamic",
        use_container_width=True,
        key="editor_final_layout"
    )
    st.session_state['current_df'] = edited_df
    
    # 下載按鈕 (檔名連動)
    if not edited_df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_df.to_excel(writer, index=False)
        st.download_button(
            label=f"💾 儲存並下載 {c_name} 的專屬 Excel",
            data=output.getvalue(),
            file_name=f"{c_name}_{c_age}歲_保單.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.divider()
    # 下方參考視窗保持不變
    st.subheader("🔍 參考視窗 (PDF/圖片內容)")
    if uploaded_file:
        f_type = uploaded_file.name.split('.')[-1].lower()
        if f_type == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                text = "".join([page.extract_text() for page in pdf.pages])
            st.text_area("PDF 內容", value=text, height=400)
        elif f_type in ['png', 'jpg', 'jpeg']:
            st.image(Image.open(uploaded_file), use_container_width=True)
        elif f_type == 'xlsx':
            if st.button("確認載入此 Excel 資料"):
                st.session_state['current_df'] = pd.read_excel(uploaded_file)
                st.rerun()

# --- 模式 2：診斷報告 ---
elif mode == "2. 產出理賠診斷報告":
    df = st.session_state['current_df']
    name = st.session_state.get('c_name', "新客戶") # 從錄入頁抓取姓名
    if df.empty:
        st.warning("⚠️ 請先在錄入頁面輸入資料。")
    else:
        title_gender = "先生" if c_gender == "男" else "小姐"
        st.header(f"📊 {name} {title_gender} ({c_age}歲) 保障診斷報告")
        
        # 數據統計與圖表
        total_p = df["保費"].sum()
        total_benefit = pd.to_numeric(df["預估理賠額(萬)"], errors='coerce').sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("年度總保費", f"{total_p:,} 元")
        c2.metric("預估總保障價值", f"{total_benefit:,.0f} 萬元")
        c3.metric("平均月繳", f"{int(total_p/12):,} 元")
        st.divider()
        l_col, r_col = st.columns([1.2, 1])
        with l_col:
            cats = ["壽險", "意外", "醫療", "重疾", "長照"]
            vals = [pd.to_numeric(df[df['類別'] == c]['預估理賠額(萬)'], errors='coerce').sum() for c in cats]
            fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])))
            st.plotly_chart(fig, use_container_width=True)
        with r_col:
            st.subheader("💡 診斷建議")
            for c, v in zip(cats, vals):
                if v == 0: st.error(f"❌ **{c}缺口**")
                elif v < 100: st.warning(f"⚠️ **{c}偏低**")
                else: st.success(f"✅ **{c}充足**")
