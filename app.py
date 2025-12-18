import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# --- 側邊欄：基本資料與檔案載入 ---
with st.sidebar:
    st.header("👤 客戶基本資料")
    # 這裡的輸入會儲存在 session_state['c_name'] 中，並與下方標題連動
    st.session_state['c_name'] = st.text_input("客戶姓名", value=st.session_state.get('c_name', "新客戶"))
    st.session_state['c_age'] = st.number_input("投保年齡", value=st.session_state.get('c_age', 27))
    st.session_state['c_gender'] = st.selectbox("性別", ["男", "女"], index=0 if st.session_state.get('c_gender') == "男" else 1)
    
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
    # 修正重點：這裡的標題會根據 st.session_state['c_name'] 動態變化
    st.header(f"📝 正在建立 {st.session_state['c_name']} 的保單明細表")
    
    # 編輯區
    edited_df = st.data_editor(
        st.session_state['current_df'],
        num_rows="dynamic",
        use_container_width=True,
        key="editor_final"
    )
    st.session_state['current_df'] = edited_df
    
    if not edited_df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_df.to_excel(writer, index=False)
        st.download_button(
            label=f"💾 下載 {st.session_state['c_name']} 的專屬存檔",
            data=output.getvalue(),
            file_name=f"{st.session_state['c_name']}_{st.session_state['c_age']}歲_保單.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.divider()

    # 下方：參考視窗
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
            if st.button("確認從 Excel 載入資料"):
                st.session_state['current_df'] = pd.read_excel(uploaded_file)
                st.rerun()
    else:
        st.info("💡 尚未上傳檔案。上傳後內容會顯示在此。")

# --- 模式 2：診斷報告 ---
elif mode == "2. 產出理賠診斷報告":
    df = st.session_state['current_df']
    if df.empty:
        st.warning("⚠️ 請先在錄入頁面輸入資料。")
    else:
        t_gender = "先生" if st.session_state['c_gender'] == "男" else "小姐"
        # 報告頁面的標題也會同步
        st.header(f"📊 {st.session_state['c_name']} {t_gender} ({st.session_state['c_age']}歲) 保障診斷報告")
        
        # (其餘報告代碼保持不變...)
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
