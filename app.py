import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="專業保單診斷系統", layout="wide")

# --- 側邊欄：檔案與基本資料 ---
with st.sidebar:
    st.header("👤 客戶基本資料")
    # 使用 session_state 確保資料在分頁切換時被保留
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
    ref_col, edit_col = st.columns([1, 1.2])
    
    with ref_col:
        st.subheader("🔍 參考視窗")
        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            if file_type == 'pdf':
                with pdfplumber.open(uploaded_file) as pdf:
                    text = "".join([page.extract_text() for page in pdf.pages])
                st.text_area("提取內容", value=text, height=500)
            elif file_type in ['png', 'jpg', 'jpeg']:
                st.image(Image.open(uploaded_file), use_container_width=True)
            elif file_type == 'xlsx':
                st.session_state['current_df'] = pd.read_excel(uploaded_file)
                st.success("Excel 載入成功！")
        else:
            st.info("請在此上傳客戶原始資料。")

    with edit_col:
        st.subheader("📋 編輯區")
        edited_df = st.data_editor(
            st.session_state['current_df'],
            num_rows="dynamic",
            use_container_width=True,
            key="editor_v5"
        )
        st.session_state['current_df'] = edited_df
        
        # 下載 Excel (檔名包含姓名)
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

# --- 模式 2：診斷報告 ---
elif mode == "2. 產出理賠診斷報告":
    df = st.session_state['current_df']
    if df.empty:
        st.warning("⚠️ 請先在第一頁輸入保單資料。")
    else:
        title_gender = "先生" if st.session_state['c_gender'] == "男" else "小姐"
        st.header(f"📊 {st.session_state['c_name']} {title_gender} ({st.session_state['c_age']}歲) 保障診斷報告")
        
        total_p = df["保費"].sum()
        total_benefit = pd.to_numeric(df["預估理賠額(萬)"], errors='coerce').sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("年度總保費", f"{total_p:,} 元")
        c2.metric("預估總保障額度", f"{total_benefit:,.0f} 萬元")
        c3.metric("平均月繳", f"{int(total_p/12):,} 元")

        st.divider()
        
        left_p, right_p = st.columns([1.2, 1])
        with left_p:
            all_cats = ["壽險", "意外", "醫療", "重疾", "長照"]
            radar_values = [pd.to_numeric(df[df['類別'] == cat]['預估理賠額(萬)'], errors='coerce').sum() for cat in all_cats]
            
            fig = go.Figure(data=go.Scatterpolar(r=radar_values, theta=all_cats, fill='toself', name='理賠(萬)'))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, max(radar_values)*1.2 if max(radar_values)>0 else 100])),
                title="全方位保障價值分布 (萬元)"
            )
            st.plotly_chart(fig, use_container_width=True)

        with right_p:
            st.subheader(f"💡 給 {st.session_state['c_name']} 的專家建議")
            for cat, val in zip(all_cats, radar_values):
                if val == 0:
                    st.error(f"❌ **{cat}缺口**：尚未規畫任何保障。")
                elif val < 100:
                    st.warning(f"⚠️ **{cat}偏低**：現有 {val} 萬，建議提高額度。")
                else:
                    st.success(f"✅ **{cat}充足**：已具備 {val} 萬保障。")
