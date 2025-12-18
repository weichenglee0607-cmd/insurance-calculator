import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 保險全能診斷系統", layout="wide")

# --- 側邊欄：檔案上傳區 ---
with st.sidebar:
    st.header("📂 檔案載入中心")
    uploaded_file = st.file_uploader("支援圖片、PDF 或 Excel", type=["pdf", "xlsx", "png", "jpg", "jpeg"])
    
    st.divider()
    mode = st.radio("功能切換：", ["1. 資料錄入與對照", "2. 保障雷達圖分析"])

# --- 初始化資料 ---
if 'current_df' not in st.session_state:
    st.session_state['current_df'] = pd.DataFrame(columns=["險種名稱", "類別", "保費", "期滿(民國)"])

# --- 模式 1：資料錄入與對照 ---
if mode == "1. 資料錄入與對照":
    st.header("📝 保單資料錄入")
    
    # 建立左右兩欄：左邊看參考資料，右邊編輯表格
    ref_col, edit_col = st.columns([1, 1.2])
    
    with ref_col:
        st.subheader("🔍 參考資料視窗")
        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            
            if file_type == 'pdf':
                with pdfplumber.open(uploaded_file) as pdf:
                    text = "".join([page.extract_text() for page in pdf.pages])
                st.text_area("PDF 文字提取內容", value=text, height=500)
                
            elif file_type in ['png', 'jpg', 'jpeg']:
                image = Image.open(uploaded_file)
                st.image(image, caption="保單截圖預覽", use_container_width=True)
                
            elif file_type == 'xlsx':
                st.session_state['current_df'] = pd.read_excel(uploaded_file)
                st.success("Excel 載入成功！請在右側檢查。")
        else:
            st.info("請上傳檔案，此處將顯示參考內容。")

    with edit_col:
        st.subheader("📋 編輯保單明細")
        client_name = st.text_input("客戶姓名", value="新客戶")
        
        # 編輯器
        edited_df = st.data_editor(
            st.session_state['current_df'],
            num_rows="dynamic",
            use_container_width=True,
            key="editor_v3"
        )
        st.session_state['current_df'] = edited_df
        
        # 下載 Excel
        if not edited_df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                edited_df.to_excel(writer, index=False)
            st.download_button(
                label="💾 下載並儲存此客戶 Excel",
                data=output.getvalue(),
                file_name=f"{client_name}_保單.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- 模式 2：保障雷達圖分析 ---
elif mode == "2. 保障雷達圖分析":
    st.header("🕸️ 全方位保障分析")
    df = st.session_state['current_df']
    
    if not df.empty and "類別" in df.columns:
        all_cats = ["壽險", "意外", "醫療", "重疾", "長照"]
        values = [df[df['類別'] == cat]['保費'].sum() for cat in all_cats]

        fig = go.Figure(data=go.Scatterpolar(r=values, theta=all_cats, fill='toself', line_color='#1f77b4'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(values)+1000 if max(values)>0 else 10000])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠️ 請先在錄入頁面填寫資料並選擇『類別』")
