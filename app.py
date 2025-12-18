import streamlit as st
import pandas as pd
import io

# 網頁基礎配置
st.set_page_config(page_title="專業保單診斷系統", layout="wide")

st.title("🛡️ 專業保單診斷系統")

# --- 初始化 Session State (確保資料在切換分頁時不會消失) ---
if 'current_df' not in st.session_state:
    st.session_state['current_df'] = pd.DataFrame(columns=["險種名稱", "保額/單位", "保費", "期滿(民國)"])
if 'client_name' not in st.session_state:
    st.session_state['client_name'] = "新客戶"

# --- 側邊欄：功能選單 ---
with st.sidebar:
    st.header("📂 客戶資料管理")
    mode = st.radio("功能選擇：", ["1. 載入與輸入資料", "2. 查看診斷報告"])
    
    st.divider()
    # 範例資料 (吳小姐)
    if st.button("載入吳小姐範本資料"):
        sample_data = {
            "險種名稱": ["LTN 長照終身", "ADE 意外失能", "AHI 意外住院", "HSME 醫療實支(E)", "OMR 意外實支", "SDCA 重大傷病", "WP 豁免附約"],
            "保額/單位": ["10,000", "1,000,000", "20單位", "1單位", "100,000", "2,000,000", "-"],
            "保費": [25930, 980, 1100, 21159, 1974, 14400, 1028],
            "期滿(民國)": [143, 164, 164, 169, 164, 123, 143]
        }
        st.session_state['current_df'] = pd.DataFrame(sample_data)
        st.session_state['client_name'] = "吳○君"
        st.rerun()

# --- 模式 1：載入與輸入資料 ---
if mode == "1. 載入與輸入資料":
    st.header("👤 客戶資料錄入")
    
    col_name, col_upload = st.columns([1, 1])
    with col_name:
        st.session_state['client_name'] = st.text_input("輸入新客戶姓名", value=st.session_state['client_name'])
    
    with col_upload:
        # 讀取舊客戶 Excel
        uploaded_file = st.file_uploader("📂 從 iPad 上傳舊客戶 Excel 檔", type="xlsx")
        if uploaded_file is not None:
            st.session_state['current_df'] = pd.read_excel(uploaded_file)
            st.success("✅ 已讀取舊客戶存檔")

    st.divider()
    st.subheader("📝 編輯保單明細")
    st.info("提示：直接在下方表格修改數值，或點擊表格底部 '+' 號新增險種。")
    
    # 動態表格編輯器
    edited_df = st.data_editor(
        st.session_state['current_df'], 
        num_rows="dynamic", 
        use_container_width=True,
        key="main_editor"
    )
    st.session_state['current_df'] = edited_df

    # 存檔按鈕
    if not st.session_state['current_df'].empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state['current_df'].to_excel(writer, index=False, sheet_name='保單明細')
        
        st.download_button(
            label=f"💾 儲存並下載 {st.session_state['client_name']} 的 Excel 檔案",
            data=output.getvalue(),
            file_name=f"{st.session_state['client_name']}_保單資料.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --- 模式 2：查看診斷報告 ---
elif mode == "2. 產出分析報告":
    df = st.session_state['current_df']
    if df.empty:
        st.warning("⚠️ 目前尚無資料，請先至「1. 載入與輸入資料」進行填寫。")
    else:
        st.header(f"📊 {st.session_state['client_name']} 的保障分析報告")
        
        total_p = df["保費"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("年度保費總計", f"{total_p:,} 元")
        c2.metric("月繳預估負擔", f"{int(total_p/12):,} 元")
        c3.metric("保單總項數", f"{len(df)} 項")
        
        st.divider()
        
        tab_chart, tab_table = st.tabs(["📈 保費占比分析", "📄 原始資料核對"])
        with tab_chart:
            st.bar_chart(df.set_index("險種名稱")["保費"])
        with tab_table:
            st.dataframe(df, use_container_width=True)

        st.caption("💡 建議：談完後點擊左側「1. 載入與輸入資料」底部的儲存按鈕，將檔案保留在 iPad 中。")
