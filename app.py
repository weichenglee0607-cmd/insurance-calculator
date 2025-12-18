import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# --- 側邊欄：檔案上傳區 ---
with st.sidebar:
    st.header("📂 檔案載入中心")
    uploaded_file = st.file_uploader("支援圖片、PDF 或 Excel", type=["pdf", "xlsx", "png", "jpg", "jpeg"])
    st.divider()
    mode = st.radio("功能切換：", ["1. 資料錄入與對照", "2. 產出理賠診斷報告"])

# --- 初始化資料結構 (新增理賠額度欄位) ---
if 'current_df' not in st.session_state:
    st.session_state['current_df'] = pd.DataFrame(columns=[
        "險種名稱", "類別", "保費", "預估理賠額(萬)", "期滿(民國)"
    ])

# --- 模式 1：資料錄入與對照 ---
if mode == "1. 資料錄入與對照":
    st.header("📝 保單資料錄入")
    ref_col, edit_col = st.columns([1, 1.2])
    
    with ref_col:
        st.subheader("🔍 參考資料視窗")
        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            if file_type == 'pdf':
                with pdfplumber.open(uploaded_file) as pdf:
                    text = "".join([page.extract_text() for page in pdf.pages])
                st.text_area("PDF 文字內容", value=text, height=500)
            elif file_type in ['png', 'jpg', 'jpeg']:
                st.image(Image.open(uploaded_file), use_container_width=True)
            elif file_type == 'xlsx':
                st.session_state['current_df'] = pd.read_excel(uploaded_file)
                st.success("Excel 載入成功！")
        else:
            st.info("請上傳檔案，此處將顯示參考內容。")

    with edit_col:
        st.subheader("📋 編輯保單與保障額度")
        client_name = st.text_input("客戶姓名", value="新客戶")
        
        edited_df = st.data_editor(
            st.session_state['current_df'],
            num_rows="dynamic",
            use_container_width=True,
            key="editor_v4"
        )
        st.session_state['current_df'] = edited_df
        
        if not edited_df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                edited_df.to_excel(writer, index=False)
            st.download_button(
                label=f"💾 儲存並下載 {client_name} 的 Excel",
                data=output.getvalue(),
                file_name=f"{client_name}_保單診斷.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- 模式 2：產出理賠診斷報告 ---
elif mode == "2. 產出理賠診斷報告":
    df = st.session_state['current_df']
    if df.empty:
        st.warning("⚠️ 請先在錄入頁面填寫資料。")
    else:
        st.header(f"📊 {st.session_state['client_name'] if 'client_name' in st.session_state else '客戶'} 的保障價值分析")
        
        # 統計數據
        total_p = df["保費"].sum()
        total_benefit = pd.to_numeric(df["預估理賠額(萬)"], errors='coerce').sum()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("年度保費支出", f"{total_p:,} 元")
        with c2:
            st.metric("總預估保障價值", f"{total_benefit:,.0f} 萬元")
        with c3:
            ratio = (total_p / (total_benefit * 10000)) * 100 if total_benefit > 0 else 0
            st.metric("保障槓桿比", f"{ratio:.2f}%", help="保費佔保障額度的比例，越低代表槓桿越高")

        st.divider()
        
        # 左右佈局：左雷達圖，右建議
        left_p, right_p = st.columns([1.2, 1])
        with left_p:
            all_cats = ["壽險", "意外", "醫療", "重疾", "長照"]
            # 計算各類別的理賠金額
            radar_values = [pd.to_numeric(df[df['類別'] == cat]['預估理賠額(萬)'], errors='coerce').sum() for cat in all_cats]
            
            fig = go.Figure(data=go.Scatterpolar(r=radar_values, theta=all_cats, fill='toself', name='理賠額度(萬)'))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, max(radar_values)*1.2 if max(radar_values)>0 else 100])),
                title="各項保障理賠額度分布 (萬元)"
            )
            st.plotly_chart(fig, use_container_width=True)

        with right_p:
            st.subheader("💡 專家診斷建議")
            # 簡單的邏輯判斷
            for cat, val in zip(all_cats, radar_values):
                if val == 0:
                    st.error(f"❌ **{cat}缺口**：目前尚未建立任何保障。")
                elif val < 100:
                    st.warning(f"⚠️ **{cat}偏低**：現有 {val} 萬保障，面對大病支出可能不足。")
                else:
                    st.success(f"✅ **{cat}充足**：已具備 {val} 萬保障。")
            
            st.info("※ 診斷建議僅供參考，請結合客戶實際經濟狀況評估。")
