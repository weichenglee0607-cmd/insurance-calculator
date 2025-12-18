import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# --- 側邊欄：檔案與基本資料 ---
with st.sidebar:
    st.header("👤 客戶基本資料")
    st.session_state['c_name'] = st.text_input("客戶姓名", value=st.session_state.get('c_name', "新客戶"))
    st.session_state['c_age'] = st.number_input("投保年齡", value=st.session_state.get('c_age', 27))
    st.session_state['c_gender'] = st.selectbox("性別", ["男", "女"], index=0 if st.session_state.get('c_gender') == "男" else 1)
    
    st.divider()
    st.header("📂 檔案載入")
    uploaded_file = st.file_uploader("上傳參考資料 (PDF/圖片/Excel)", type=["pdf", "xlsx", "png", "jpg", "jpeg"])
    
    st.divider()
    mode = st.radio("功能切換：", ["1. 資料錄入與對照", "2. 產出理賠診斷報告"])

# --- 初始化表格結構 ---
if 'current_df' not in st.session_state:
    st.session_state['current_df'] = pd.DataFrame(columns=[
        "險種名稱", "類別", "保費", "預估理賠額(萬)", "期滿(民國)"
    ])

# --- 模式 1：資料錄入 ---
if mode == "1. 資料錄入與對照":
    st.header(f"📝 正在建立 {st.session_state['c_name']} 的保單明細")
    
    # --- 上方：超寬編輯區 ---
    st.subheader("📋 編輯區 (表格已寬度最大化)")
    edited_df = st.data_editor(
        st.session_state['current_df'],
        num_rows="dynamic",
        use_container_width=True,
        key="editor_v6"
    )
    st.session_state['current_df'] = edited_df
    
    # 下載按鈕
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

    st.divider() # 加入分隔線

    # --- 下方：參考視窗 ---
    st.subheader("🔍 參考視窗 (置於下方以便對照)")
    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1].lower()
        if file_type == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                text = "".join([page.extract_text() for page in pdf.pages])
            st.text_area("PDF 提取文字", value=text, height=400)
        elif file_type in ['png', 'jpg', 'jpeg']:
            st.image(Image.open(uploaded_file), caption="上傳的圖片內容", use_container_width=True)
        elif file_type == 'xlsx':
            # 如果上傳的是 Excel，自動更新表格
            if st.button("確認載入此 Excel 資料"):
                st.session_state['current_df'] = pd.read_excel(uploaded_file)
                st.rerun()
            st.success("Excel 偵測成功，請點擊上方按鈕載入。")
    else:
        st.info("💡 尚未上傳參考檔案。上傳後，內容會顯示在此處。")

# --- 模式 2：診斷報告 ---
elif mode == "2. 產出理賠診斷報告":
    df = st.session_state['current_df']
    if df.empty:
        st.warning("⚠️ 請先在第一頁輸入保單資料。")
    else:
        title_gender = "先生" if st.session_state['c_gender'] == "男" else "小姐"
        st.header(f"📊 {st.session_state['c_name']} {title_gender} ({st.
