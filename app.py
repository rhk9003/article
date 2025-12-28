import streamlit as st
import pandas as pd
from docx import Document
from io import BytesIO

# --- 設定頁面配置 ---
st.set_page_config(layout="wide", page_title="文章修訂協作工具 v2", page_icon="📝")

# --- CSS 優化 (讓勾選框跟文字對齊得更好) ---
st.markdown("""
<style>
    .stCheckbox { padding-top: 10px; }
    .element-container { margin-bottom: -10px; }
</style>
""", unsafe_allow_html=True)

# --- Session State 初始化 ---
if 'doc_data' not in st.session_state:
    st.session_state['doc_data'] = [] # List of dicts: {'id': int, 'text': str, 'style': str}
if 'revisions' not in st.session_state:
    st.session_state['revisions'] = [] 
if 'next_id' not in st.session_state:
    st.session_state['next_id'] = 1
# 用於暫存被勾選的段落 ID
if 'selected_para_ids' not in st.session_state:
    st.session_state['selected_para_ids'] = []

# --- 輔助函式 ---

def read_file(uploaded_file):
    """讀取檔案並嘗試保留基本格式資訊"""
    doc_data = []
    
    if uploaded_file.name.endswith('.docx'):
        doc = Document(uploaded_file)
        for i, p in enumerate(doc.paragraphs):
            if p.text.strip(): # 忽略完全空行
                # 簡單判斷樣式以對應 Markdown
                style_name = p.style.name
                md_prefix = ""
                if 'Heading 1' in style_name: md_prefix = "# "
                elif 'Heading 2' in style_name: md_prefix = "## "
                elif 'Heading 3' in style_name: md_prefix = "### "
                elif 'List Bullet' in style_name: md_prefix = "* "
                elif 'List Number' in style_name: md_prefix = "1. "
                
                doc_data.append({
                    'id': i,
                    'text': p.text,
                    'display_text': md_prefix + p.text, # 用於預覽
                    'raw_text': p.text # 用於編輯
                })
    elif uploaded_file.name.endswith('.txt'):
        stringio = uploaded_file.getvalue().decode("utf-8")
        lines = stringio.split('\n')
        for i, line in enumerate(lines):
            if line.strip():
                doc_data.append({
                    'id': i,
                    'text': line,
                    'display_text': line,
                    'raw_text': line
                })
        
    return doc_data

def generate_report(doc_data, revisions):
    """生成 Word 報告"""
    doc = Document()
    doc.add_heading('文章修訂建議報告', 0)
    
    # 原始文章區 (嘗試還原純文字結構)
    doc.add_heading('原始文章內容', level=1)
    for item in doc_data:
        doc.add_paragraph(item['text'])
    
    doc.add_page_break()
    
    # 修改建議區
    doc.add_heading('修訂需求清單', level=1)
    
    if not revisions:
        doc.add_paragraph("無修訂內容。")
    else:
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = '編號'
        hdr_cells[1].text = '原始選取文字 (Target)'
        hdr_cells[2].text = '修改指示/建議 (Instruction)'
        
        for rev in revisions:
            row_cells = table.add_row().cells
            row_cells[0].text = str(rev['id'])
            row_cells[1].text = rev['target']
            row_cells[2].text = rev['instruction']
            
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 側邊欄 Sidebar ---

st.sidebar.title("🛠️ 修訂導航")

# 模式切換
mode_options = ["📄 閱讀與選取模式"]
for rev in st.session_state['revisions']:
    preview = (rev['target'][:15] + '..') if len(rev['target']) > 15 else rev['target']
    mode_options.append(f"#{rev['id']} 修訂: {preview}")

selection = st.sidebar.radio("功能選單：", mode_options)

st.sidebar.markdown("---")
# 下載按鈕
if st.session_state['doc_data']:
    docx_file = generate_report(st.session_state['doc_data'], st.session_state['revisions'])
    st.sidebar.download_button(
        label="📥 下載 Word 報告",
        data=docx_file,
        file_name="revision_report_v2.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# --- 主頁面 Main Area ---

if not st.session_state['doc_data']:
    st.header("1. 上傳文章")
    st.info("支援 .docx (可保留標題層級) 與 .txt")
    uploaded_file = st.file_uploader("請上傳檔案", type=['docx', 'txt'])
    
    if uploaded_file is not None:
        data = read_file(uploaded_file)
        st.session_state['doc_data'] = data
        st.rerun()

else:
    # --- 閱讀與選取模式 ---
    if selection == "📄 閱讀與選取模式":
        st.title("文章閱讀與標記")
        
        col_main, col_action = st.columns([3, 1])
        
        with col_action:
            # 浮動操作區 (固定在右側或上方)
            st.markdown("### ⚡ 操作區")
            st.caption("勾選左側文章段落後，點擊下方按鈕：")
            
            if st.button("➕ 將勾選段落加入修訂", type="primary"):
                # 收集所有被勾選的段落
                selected_texts = []
                # 遍歷 session_state 找出 checkbox 被勾選的 key
                for item in st.session_state['doc_data']:
                    key = f"chk_{item['id']}"
                    if st.session_state.get(key, False):
                        selected_texts.append(item['raw_text'])
                        # 重置勾選狀態 (可選)
                        st.session_state[key] = False
                
                if selected_texts:
                    # 合併文字
                    combined_text = "\n\n".join(selected_texts)
                    
                    # 建立新修訂
                    new_rev = {
                        'id': st.session_state['next_id'],
                        'target': combined_text,
                        'instruction': "" # 預設為空，待填寫
                    }
                    st.session_state['revisions'].append(new_rev)
                    
                    # 強制跳轉到該修訂的編輯頁面
                    # 這裡我們用一個 trick：透過 query params 或直接 rerun 來讓 sidebar 邏輯抓到最新的
                    st.session_state['next_id'] += 1
                    st.success(f"已建立修訂 #{new_rev['id']}，請在側邊欄點選進行編輯！")
                    st.rerun()
                else:
                    st.warning("請先在左側勾選至少一個段落！")

            if st.button("🧹 清除所有勾選"):
                 for item in st.session_state['doc_data']:
                    key = f"chk_{item['id']}"
                    if key in st.session_state:
                        st.session_state[key] = False
                 st.rerun()
            
            st.markdown("---")
            st.button("🔄 上傳新文件", on_click=lambda: st.session_state.clear())

        with col_main:
            st.subheader("文件預覽")
            st.markdown("請勾選想要修改的段落：")
            
            # 迭代顯示每一段
            for item in st.session_state['doc_data']:
                c1, c2 = st.columns([0.5, 9.5])
                with c1:
                    # Checkbox key 綁定段落 ID
                    st.checkbox("", key=f"chk_{item['id']}")
                with c2:
                    # 使用 Markdown 渲染保留標題大小、粗體等
                    st.markdown(item['display_text'])

    # --- 編輯修訂模式 ---
    else:
        # 解析選中的 ID
        selected_id = int(selection.split(" ")[0].replace("#", ""))
        current_rev = next((item for item in st.session_state['revisions'] if item['id'] == selected_id), None)
        
        if current_rev:
            st.title(f"編輯修訂項目 #{selected_id}")
            
            st.label_visibility = "visible"
            st.caption("這是您剛才勾選的範圍：")
            st.text_area("原始選取文字", value=current_rev['target'], height=150, disabled=True)
            
            st.subheader("👇 請輸入修改建議")
            new_instruction = st.text_area(
                "例如：請將這段語氣改得更正式，並補充數據...", 
                value=current_rev['instruction'], 
                height=200,
                key=f"inst_{selected_id}" # 使用 unique key 避免衝突
            )
            
            col_save, col_del = st.columns([1, 4])
            with col_save:
                if st.button("💾 儲存內容"):
                    # 更新 List
                    for item in st.session_state['revisions']:
                        if item['id'] == selected_id:
                            item['instruction'] = new_instruction
                    st.success("已儲存！")
            
            with col_del:
                if st.button("🗑️ 刪除此修訂"):
                    st.session_state['revisions'] = [item for item in st.session_state['revisions'] if item['id'] != selected_id]
                    st.rerun()
