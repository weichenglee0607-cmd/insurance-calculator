import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# --- 初始化表格結構 (預設包含核心欄位) ---
if 'current_df' not in st.session_state:
    st.session_state['current_df'] = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "範例保單", "類別": "醫療", "保費 (年繳)": 0, "預估理賠額 (萬)": 0, "期滿 (民國)": 113}
    ])

# --- 側邊欄：基本設定與檔案載入 ---
with st.sidebar:
    st.header("👤 基本資料設定")
    st.session_state['c_age'] = st.number_input("投保年齡", value=st.session_state.get('c_age', 27))
    st.session_state['c_gender'] = st.selectbox("性別", ["男", "女"])
    
    st.divider()
    st.header("📂 檔案載入")
    uploaded_file = st.file_uploader("上傳 PDF/圖片/Excel", type=["pdf", "xlsx", "png", "jpg", "jpeg"])
    
    st.divider()
    mode = st.radio("功能切換：", ["1. 資料錄入與對照", "2. 產出理賠診斷報告"])

# --- 模式 1：資料錄入 ---
if mode == "1. 資料錄入與對照":
    # 這裡的邏輯：標題優先抓取表格第一行的姓名
    df_input = st.session_state['current_df']
    current_name = df_input['姓名'].iloc[0] if '姓名' in df_input.columns else "新客戶"
    
    st.header(f"📝 {current_name} 的保單明細表")
    
    # 編輯表格區
    edited_df = st.data_editor(
        st.session_state['current_df'],
        num_rows="dynamic",
        use_container_width=True,
        key="editor_final_v1"
    )
    st.session_state['current_df'] = edited_df
    
    # 下載按鈕 (檔名連動)
    if not edited_df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_df.to_excel(writer, index=False)
        st.download_button(
            label=f"💾 儲存並下載 {current_name} 的專屬 Excel",
            data=output.getvalue(),
            file_name=f"{current_name}_保單.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.divider()
    st.subheader("🔍 參考視窗")
    if uploaded_file:
        f_type = uploaded_file.name.split('.')[-1].lower()
        if f_type == 'xlsx':
            if st.button("✅ 確認載入 Excel 資料"):
                st.session_state['current_df'] = pd.read_excel(uploaded_file)
                st.rerun()
        elif f_type == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                text = "".join([page.extract_text() for page in pdf.pages])
            st.text_area("PDF 文字內容", value=text, height=300)
        elif f_type in ['png', 'jpg', 'jpeg']:
            st.image(Image.open(uploaded_file), use_container_width=True)

# --- 模式 2：診斷報告 (修復 KeyError) ---
elif mode == "2. 產出理賠診斷報告":
    df = st.session_state['current_df'].copy()
    
    # 關鍵防錯：強制統一欄位名稱
    rename_map = {
        "保費 (年繳)": "保費",
        "保費": "保費",
        "預估理賠額 (萬)": "理賠",
        "理賠": "理賠"
    }
    # 檢查並重新命名現有欄位
    new_cols = {c: rename_map[c] for c in df.columns if c in rename_map}
    df.rename(columns=new_cols, inplace=True)
    
    # 定義報告抬頭名字 (修正 KeyError: '客戶')
    report_name = df['姓名'].iloc[0] if '姓名' in df.columns else "客戶"
    
    if "保費" not in df.columns:
        st.warning("⚠️ 找不到『保費』相關欄位，請檢查表格標題是否正確。")
    else:
        st.header(f"📊 {report_name} 專屬保障診斷報告")
        
        # 數值清理
        df["保費"] = pd.to_numeric(df["保費"], errors='coerce').fillna(0)
        df["理賠"] = pd.to_numeric(df.get("理賠", 0), errors='coerce').fillna(0)
        
        total_p = df["保費"].sum()
        total_benefit = df["理賠"].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("年度總保費", f"{total_p:,} 元")
        c2.metric("預估總保障額度", f"{total_benefit:,.0f} 萬元")
        c3.metric("投保年齡", f"{st.session_state['c_age']} 歲")

        st.divider()
        
        l_col, r_col = st.columns([1.2, 1])
        with l_col:
            cats = ["壽險", "意外", "醫療", "重疾", "長照"]
            # 確保類別欄位存在
            if '類別' in df.columns:
                vals = [df[df['類別'] == c]['理賠'].sum() for c in cats]
                fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("請在表格中填寫『類別』以繪製雷達圖。")

        with r_col:
            st.subheader("💡 診斷建議")
            if '類別' in df.columns:
                for c, v in zip(cats, vals):
                    if v == 0: st.error(f"❌ **{c}缺口**")
                    elif v < 100: st.warning(f"⚠️ **{c}偏低** ({v}萬)")
                    else: st.success(f"✅ **{c}充足** ({v}萬)")
