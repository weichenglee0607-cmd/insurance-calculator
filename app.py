import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go

st.set_page_config(page_title="AI 保單分析診斷系統", layout="wide")

# --- 核心邏輯：PDF 解析 ---
def parse_insurance_pdf(file):
    with pdfplumber.open(file) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text()
    
    # 這裡可以加入更複雜的規則來抓取特定欄位，目前先做文字快照
    st.sidebar.success("PDF 讀取成功！")
    return full_text

# --- 初始化資料 ---
if 'current_df' not in st.session_state:
    st.session_state['current_df'] = pd.DataFrame(columns=["險種名稱", "類別", "保費"])

# --- 側邊欄 ---
with st.sidebar:
    st.header("🤖 AI 助手")
    uploaded_pdf = st.file_uploader("上傳客戶保單 PDF", type="pdf")
    if uploaded_pdf:
        pdf_content = parse_insurance_pdf(uploaded_pdf)
        st.expander("查看 PDF 原始文字").write(pdf_content)
        st.info("💡 目前已具備讀取能力，您可以根據左側文字手動快速填入右側表格。")

    mode = st.radio("導覽：", ["資料輸入", "保障雷達圖分析"])

# --- 模式 1：資料輸入 (包含類別欄位) ---
if mode == "資料輸入":
    st.header("📝 保單明細錄入")
    # 定義險種大類，用於雷達圖
    categories = ["壽險", "意外", "醫療", "重疾", "長照"]
    
    # 如果表格是空的，預設給一些欄位
    if st.session_state['current_df'].empty:
        st.session_state['current_df'] = pd.DataFrame([
            {"險種名稱": "範例保單", "類別": "醫療", "保費": 5000}
        ])

    edited_df = st.data_editor(
        st.session_state['current_df'],
        num_rows="dynamic",
        use_container_width=True
    )
    st.session_state['current_df'] = edited_df

# --- 模式 2：保障雷達圖 ---
elif mode == "保障雷達圖分析":
    st.header("🕸️ 保障缺口雷達圖")
    df = st.session_state['current_df']
    
    if not df.empty and "類別" in df.columns:
        # 根據類別統計保費占比（作為保障強度指標）
        radar_data = df.groupby("類別")["保費"].sum().reset_index()
        
        # 確保所有類別都出現，即使金額為 0
        all_cats = ["壽險", "意外", "醫療", "重疾", "長照"]
        values = []
        for cat in all_cats:
            val = radar_data[radar_data['類別'] == cat]['保費'].sum()
            values.append(val)

        # 畫雷達圖
        fig = go.Figure(data=go.Scatterpolar(
          r=values,
          theta=all_cats,
          fill='toself',
          name='保障強度'
        ))

        fig.update_layout(
          polar=dict(radialaxis=dict(visible=True, range=[0, max(values) if max(values)>0 else 10000])),
          showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        st.write("💡 數值越高代表該項目的投入預算（保障強度）越高。")
    else:
        st.warning("請先在輸入頁面設定『類別』與『保費』")
