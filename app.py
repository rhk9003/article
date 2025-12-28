import streamlit as st
import pandas as pd
from docx import Document
from io import BytesIO

# --- 設定頁面配置 ---
st.set_page_config(layout="wide", page_title="文章修訂協作工具", page_icon="📝")

# --- Session State 初始化 ---
# 用於儲存文章內容與修改清單
if 'article_text' not in st.session_state:
    st.session_state['article_text'] = ""
if 'article_paragraphs' not in st.session_state:
    st.session_state['article_paragraphs'] = []
if 'revisions' not in st.session_state:
    st.session_state['revisions'] = [] # List of dicts: {'id': int, 'target': str, 'instruction': str}
if 'next_id' not in st.session_state:
    st.session_state['next_id'] = 1

# --- 輔助函式 ---

def read_file(uploaded_file):
    """讀取 txt 或 docx 檔案並回傳文字內容與段落清單"""
    text = ""
    paragraphs = []
    
    if uploaded_file.name.endswith('.docx'):
        doc = Document(uploaded_file)
        for p in doc.paragraphs:
            if p.text.strip(): # 忽略空行
                paragraphs.append(p.text)
        text = "\n\n".join(paragraphs)
    elif uploaded_file.name.endswith('.txt'):
        stringio = uploaded_file.getvalue().decode("utf-8")
        text = stringio
        paragraphs = [p for p in text.split('\n') if p.strip()]
        
    return text, paragraphs

def generate_report(original_text, revisions):
    """生成包含原始文章與修改建議的 Word 檔案"""
    doc = Document()
    
    # 標題
    doc.add_heading('文章修訂建議報告', 0)
    
    # 原始文章區
    doc.add_heading('原始文章內容', level=1)
    doc.add_paragraph(original_text)
    
    doc.add_page_break()
    
    # 修改建議區
    doc.add_heading('修訂需求清單', level=1)
    
    if not revisions:
        doc.add_paragraph("無修訂內容。")
    else:
        # 建立表格
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = '編號'
        hdr_cells[1].text = '原始選取文字 (Target)'
        hdr_cells[2].text = '修改指示/建議 (Instruction)'
        
        # 填入資料
        for rev in revisions:
            row_cells = table.add_row().cells
            row_cells[0].text = str(rev['id'])
            row_cells[1].text = rev['target']
            row_cells[2].text = rev['instruction']
            
    # 存入 BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 側邊欄 Sidebar ---

st.sidebar.title("🛠️ 修訂導航")

# 導航模式選擇
nav_options = ["📄 瀏覽與新增修訂"]
if st.session_state['revisions']:
    for rev in st.session_state['revisions']:
        # 截斷過長的文字以優化顯示
        preview = (rev['target'][:15] + '..') if len(rev['target']) > 15 else rev['target']
        nav_options.append(f"#{rev['id']} 修訂: {preview}")

selection = st.sidebar.radio("選擇操作或編輯項目：", nav_options)

# 顯示匯出按鈕 (放在側邊欄底部)
st.sidebar.markdown("---")
if st.session_state['article_text']:
    docx_file = generate_report(st.session_state['article_text'], st.session_state['revisions'])
    st.sidebar.download_button(
        label="📥 下載 Word 修訂報告",
        data=docx_file,
        file_name="revision_report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# --- 主頁面 Main Area ---

# 1. 檔案上傳區 (僅在還沒上傳時顯示，或提供重置選項)
if not st.session_state['article_text']:
    st.header("1. 上傳文章")
    uploaded_file = st.file_uploader("請上傳 Word (.docx) 或文字檔 (.txt)", type=['docx', 'txt'])
    
    if uploaded_file is not None:
        text, paras = read_file(uploaded_file)
        st.session_state['article_text'] = text
        st.session_state['article_paragraphs'] = paras
        st.rerun()

else:
    # --- 邏輯分支：新增修訂模式 vs 編輯修訂模式 ---
    
    if selection == "📄 瀏覽與新增修訂":
        st.title("文章瀏覽與標記")
        
        # 顯示全文 (唯讀，方便閱讀)
        with st.expander("點擊展開/收合完整文章內容", expanded=True):
            st.text_area("全文預覽", value=st.session_state['article_text'], height=300, disabled=True)
        
        st.markdown("---")
        st.header("➕ 加入新的修改項目")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.info("方式 A：從段落清單選取")
            # 讓使用者選擇段落，自動填入下方文字框
            selected_para = st.selectbox(
                "選擇要修改的段落 (預覽)", 
                options=["-- 請選擇 --"] + st.session_state['article_paragraphs'],
                index=0
            )
        
        with col2:
            st.info("方式 B：手動複製貼上")
            st.markdown("您可以直接從上方全文複製任何片段貼入下方。")

        # 決定預設值
        default_target = ""
        if selected_para and selected_para != "-- 請選擇 --":
            default_target = selected_para

        # 修改目標輸入框
        target_text = st.text_area("欲修改的原始文字範圍", value=default_target, height=100, key="new_target")
        instruction_text = st.text_area("您的修改建議或指示", height=100, key="new_instruction")
        
        if st.button("建立修訂項目"):
            if target_text.strip():
                new_rev = {
                    'id': st.session_state['next_id'],
                    'target': target_text,
                    'instruction': instruction_text
                }
                st.session_state['revisions'].append(new_rev)
                st.session_state['next_id'] += 1
                st.success(f"已新增修訂項目 #{new_rev['id']}")
                st.rerun() # 重新整理以更新側邊欄
            else:
                st.error("請選取或輸入欲修改的文字範圍")

        # 重置文章按鈕
        if st.button("🔄 重置/上傳新文章", type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    else:
        # --- 編輯特定修訂項目模式 ---
        # 解析選中的 ID (格式: "#1 修訂: ...")
        selected_id = int(selection.split(" ")[0].replace("#", ""))
        
        # 找到對應的資料
        current_rev = next((item for item in st.session_state['revisions'] if item['id'] == selected_id), None)
        
        if current_rev:
            st.title(f"編輯修訂項目 #{selected_id}")
            
            st.subheader("原始選取文字 (Target)")
            st.info(current_rev['target']) # 顯示原始選取文字，不建議修改以免對不上原文
            
            st.subheader("修改指示 (Instruction)")
            # 這裡使用 key 來綁定輸入，但因為是在 loop 或動態頁面，需要小心 state 管理
            # 我們直接讀取當前值作為 default
            new_instruction = st.text_area(
                "編輯您的指示", 
                value=current_rev['instruction'], 
                height=200
            )
            
            col_save, col_del = st.columns([1, 4])
            
            with col_save:
                if st.button("💾 儲存修改"):
                    # 更新 List 中的資料
                    for item in st.session_state['revisions']:
                        if item['id'] == selected_id:
                            item['instruction'] = new_instruction
                    st.success("修改已儲存！")
            
            with col_del:
                if st.button("🗑️ 刪除此項目", type="primary"):
                    st.session_state['revisions'] = [item for item in st.session_state['revisions'] if item['id'] != selected_id]
                    st.rerun()
