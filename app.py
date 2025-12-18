import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# --- 初始化 Session State (確保切換分頁資料不消失) ---
if 'c_name' not in st.session_state:
    st.session_state['c_name'] = "新客戶"
if 'current_df' not in st.session_state:
    st.session_state['current_df'] = pd.DataFrame(columns=["險種名稱", "類別", "保費", "預估理賠額(萬)", "期滿(民國)"])

# --- 側邊欄：功能與基本資料 ---
with st.sidebar:
    st.header("👤 基本資料設定")
    # 名字欄位會根據 Excel 自動變動
    st.session_state['c_name'] = st.text_input("客戶姓名", value=st.session_state['c_name'])
    st.session_state['c_age'] = st.number_input("投保年齡", value=st.session_state.get('c_age', 27))
    st.session_state['c_gender'] = st.selectbox("性別", ["男", "女"])
    
    st.divider()
    st.header("📂 檔案載入")
    uploaded_file = st.file_uploader("上傳 PDF/圖片/Excel", type=["pdf", "xlsx", "png", "jpg", "jpeg"])
    
    st.divider()
    mode = st.radio("功能切換：", ["1. 資料錄入與對照", "2. 產出理賠診斷報告"])

# --- 模式 1：資料錄入 (表格在上、參考在下) ---
if mode == "1. 資料錄入與對照":
    # 這裡的標題會連動 st.session_state['c_name']
    st.header(f"📝 {st.session_state['c_name']} 的保單明細表")
    
    # --- 編輯表格區 ---
    edited_df = st.data_editor(
        st.session_state['current_df'],
        num_rows="dynamic",
        use_container_width=True,
        key="editor_pro_v1"
    )
    st.session_state['current_df'] = edited_df
    
    # 下載按鈕 (檔名自動帶入姓名)
    if not edited_df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_df.to_excel(writer, index=False)
        st.download_button(
            label=f"💾 儲存並下載 {st.session_state['c_name']} 的專屬 Excel",
            data=output.getvalue(),
            file_name=f"{st.session_state['c_name']}_{st.session_state['c_age']}歲_保單.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.divider()

    # --- 下方參考視窗 ---
    st.subheader("🔍 參考視窗 (PDF/圖片內容)")
    if uploaded_file:
        f_type = uploaded_file.name.split('.')[-1].lower()
        
        # 邏輯 A: 如果是 Excel，自動抓取檔名或內文中的姓名
        if f_type == 'xlsx':
            if st.button("✅ 點我：自動載入 Excel 並帶入姓名"):
                new_df = pd.read_excel(uploaded_file)
                st.session_state['current_df'] = new_df
                
                # 自動抓取檔名中的名字 (例如：張曉明_27歲_保單.xlsx -> 張曉明)
                auto_name = uploaded_file.name.split('_')[0]
                st.session_state['c_name'] = auto_name
                st.success(f"已成功載入資料，並辨識客戶為：{auto_name}")
                st.rerun()
                
        # 邏輯 B: 如果是 PDF 或圖片
        elif f_type == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                text = "".join([page.extract_text() for page in pdf.pages])
            st.text_area("PDF 提取文字", value=text, height=300)
            
        elif f_type in ['png', 'jpg', 'jpeg']:
            st.image(Image.open(uploaded_file), use_container_width=True)
    else:
        st.info("💡 尚未上傳檔案。上傳之前存好的 Excel 可自動同步姓名。")

# --- 模式 2：診斷報告 ---
elif mode == "2. 產出理賠診斷報告":
    df = st.session_state['current_df']
    if df.empty:
        st.warning("⚠️ 請先在錄入頁面輸入資料。")
    else:
        title_gender = "先生" if st.session_state['c_gender'] == "男" else "小姐"
        st.header(f"📊 {st.session_state['c_name']} {title_gender} ({st.session_state['c_age']}歲) 保障診斷報告")
        
        # 數據統計與雷達圖 (維持專業版邏輯)
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
            st.subheader("💡 專家診斷建議")
            for c, v in zip(cats, vals):
                if v == 0: st.error(f"❌ **{c}缺口**")
                elif v < 100: st.warning(f"⚠️ **{c}偏低**")
                else: st.success(f"✅ **{c}充足**")
