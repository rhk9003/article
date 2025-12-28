import streamlit as st
from docx import Document
from io import BytesIO

# --- 設定頁面配置 ---
st.set_page_config(layout="wide", page_title="文章修訂協作工具 v4", page_icon="📝")

# --- CSS 強制對齊優化 ---
# 這裡的 CSS 是關鍵：它移除了標題的上方空白，並讓 checkbox 與文字緊密排列
st.markdown("""
<style>
    /* 1. 調整 Checkbox 容器，減少多餘空白 */
    .stCheckbox {
        padding-top: 0px !important;
        margin-top: -2px !important; /* 微調向上，對齊文字基線 */
    }
    
    /* 2. 移除 Markdown 標題與段落的上方預設空白 (這是對齊關鍵) */
    div[data-testid="stMarkdownContainer"] h1, 
    div[data-testid="stMarkdownContainer"] h2, 
    div[data-testid="stMarkdownContainer"] h3, 
    div[data-testid="stMarkdownContainer"] h4, 
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] ul,
    div[data-testid="stMarkdownContainer"] li {
        margin-top: 0 !important;
        padding-top: 0 !important;
        margin-bottom: 0.5rem !important; /* 保持下方一點間距即可 */
    }

    /* 3. 讓每一行的容器有底線，增加閱讀指引 (可選，讓畫面更整齊) */
    .row-container {
        border-bottom: 1px solid #f0f2f6;
        padding-bottom: 10px;
        padding-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State 初始化 ---
if 'doc_data' not in st.session_state:
    st.session_state['doc_data'] = [] 
if 'revisions' not in st.session_state:
    st.session_state['revisions'] = [] 
if 'next_id' not in st.session_state:
    st.session_state['next_id'] = 1
if 'original_file_bytes' not in st.session_state:
    st.session_state['original_file_bytes'] = None
if 'original_filename' not in st.session_state:
    st.session_state['original_filename'] = ""
if 'global_feedback' not in st.session_state:
    st.session_state['global_feedback'] = ""

# --- 輔助函式 ---

def read_file(uploaded_file):
    """讀取檔案並解析"""
    file_bytes = uploaded_file.getvalue()
    filename = uploaded_file.name
    doc_data = []
    
    if filename.endswith('.docx'):
        doc = Document(BytesIO(file_bytes))
        for i, p in enumerate(doc.paragraphs):
            if p.text.strip(): 
                style_name = p.style.name
                md_prefix = ""
                # 為了讓預覽更好看，我們簡單映射常用標題
                if 'Heading 1' in style_name: md_prefix = "# "
                elif 'Heading 2' in style_name: md_prefix = "## "
                elif 'Heading 3' in style_name: md_prefix = "### "
                elif 'List Bullet' in style_name: md_prefix = "* "
                elif 'List Number' in style_name: md_prefix = "1. "
                
                doc_data.append({
                    'id': i,
                    'text': p.text,
                    'display_text': md_prefix + p.text,
                    'raw_text': p.text
                })
    elif filename.endswith('.txt'):
        stringio = file_bytes.decode("utf-8")
        lines = stringio.split('\n')
        for i, line in enumerate(lines):
            if line.strip():
                doc_data.append({
                    'id': i,
                    'text': line,
                    'display_text': line,
                    'raw_text': line
                })
    return doc_data, file_bytes, filename

def generate_appended_report(original_bytes, filename, global_feedback, revisions):
    """匯出追加模式報告"""
    if filename.endswith('.docx'):
        doc = Document(BytesIO(original_bytes))
    else:
        doc = Document()
        doc.add_heading('原始文字內容', level=1)
        doc.add_paragraph(original_bytes.decode("utf-8"))

    doc.add_page_break()
    doc.add_heading('【修訂建議報告】', level=0)
    
    doc.add_heading('一、整體修改建議', level=1)
    doc.add_paragraph(global_feedback if global_feedback.strip() else "（無整體建議）")
    
    doc.add_heading('二、細部修訂清單', level=1)
    if not revisions:
        doc.add_paragraph("無針對性修訂內容。")
    else:
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = '編號'
        hdr_cells[1].text = '原始選取文字'
        hdr_cells[2].text = '修改指示'
        
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

with st.sidebar.expander("📝 整體修改建議", expanded=True):
    st.session_state['global_feedback'] = st.text_area(
        "輸入整體建議：",
        value=st.session_state['global_feedback'],
        height=150
    )

st.sidebar.markdown("---")

mode_options = ["📄 閱讀與選取模式"]
for rev in st.session_state['revisions']:
    # 預覽文字處理
    preview = (rev['target'][:15] + '..') if len(rev['target']) > 15 else rev['target']
    mode_options.append(f"#{rev['id']} 修訂: {preview}")

selection = st.sidebar.radio("功能選單：", mode_options)

st.sidebar.markdown("---")

if st.session_state['original_file_bytes']:
    st.sidebar.header("📤 匯出報告")
    docx_file = generate_appended_report(
        st.session_state['original_file_bytes'], 
        st.session_state['original_filename'],
        st.session_state['global_feedback'],
        st.session_state['revisions']
    )
    output_name = f"Revised_{st.session_state['original_filename']}" if st.session_state['original_filename'].endswith('.docx') else "Revised_Report.docx"
    st.sidebar.download_button("📥 下載完整 Word 報告", data=docx_file, file_name=output_name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# --- 主頁面 Main Area ---

if not st.session_state['doc_data']:
    st.header("1. 上傳文章")
    st.info("支援 .docx 與 .txt")
    uploaded_file = st.file_uploader("請上傳檔案", type=['docx', 'txt'])
    
    if uploaded_file is not None:
        data, file_bytes, filename = read_file(uploaded_file)
        st.session_state['doc_data'] = data
        st.session_state['original_file_bytes'] = file_bytes
        st.session_state['original_filename'] = filename
        st.rerun()

else:
    if selection == "📄 閱讀與選取模式":
        st.title("文章閱讀與標記")
        
        if st.session_state['global_feedback']:
            st.info(f"💡 整體建議：{st.session_state['global_feedback']}")
        
        col_main, col_action = st.columns([3, 1])
        
        with col_action:
            st.markdown("### 操作區")
            if st.button("➕ 將勾選段落加入修訂", type="primary"):
                selected_texts = []
                for item in st.session_state['doc_data']:
                    key = f"chk_{item['id']}"
                    if st.session_state.get(key, False):
                        selected_texts.append(item['raw_text'])
                        st.session_state[key] = False
                
                if selected_texts:
                    combined_text = "\n\n".join(selected_texts)
                    new_rev = {'id': st.session_state['next_id'], 'target': combined_text, 'instruction': ""}
                    st.session_state['revisions'].append(new_rev)
                    st.session_state['next_id'] += 1
                    st.success(f"已建立修訂 #{new_rev['id']}")
                    st.rerun()
                else:
                    st.warning("請先勾選段落！")

            if st.button("🧹 清除勾選"):
                 for item in st.session_state['doc_data']:
                    key = f"chk_{item['id']}"
                    if key in st.session_state: st.session_state[key] = False
                 st.rerun()
            st.markdown("---")
            if st.button("🔄 上傳新文件"):
                st.session_state.clear()
                st.rerun()

        with col_main:
            st.subheader("文件內容")
            st.caption("請直接勾選需要修改的行：")
            
            # --- 渲染優化區 ---
            for item in st.session_state['doc_data']:
                # 使用 container 來做視覺分隔
                with st.container():
                    # 調整比例：左邊給 checkbox 的空間縮到極小 (0.3)，讓它盡量靠右貼近文字
                    c1, c2 = st.columns([0.3, 9.7])
                    with c1:
                        # label_visibility="collapsed" 隱藏 checkbox 自帶的 label 佔位
                        st.checkbox("", key=f"chk_{item['id']}")
                    with c2:
                        st.markdown(item['display_text'])
                    
                    # 每一行結束加一個極細的分隔線，幫助對齊視覺 (可選)
                    st.markdown("<hr style='margin: 0; border: none; border-top: 1px solid #eee;'/>", unsafe_allow_html=True)
                    
    else:
        # 編輯模式 (無變更)
        selected_id = int(selection.split(" ")[0].replace("#", ""))
        current_rev = next((item for item in st.session_state['revisions'] if item['id'] == selected_id), None)
        
        if current_rev:
            st.title(f"編輯修訂項目 #{selected_id}")
            st.caption("原始選取文字：")
            st.text_area("Target", value=current_rev['target'], height=150, disabled=True)
            st.subheader("👇 修改建議")
            new_instruction = st.text_area("請輸入指示...", value=current_rev['instruction'], height=200, key=f"inst_{selected_id}")
            
            col_save, col_del = st.columns([1, 4])
            with col_save:
                if st.button("💾 儲存內容"):
                    for item in st.session_state['revisions']:
                        if item['id'] == selected_id:
                            item['instruction'] = new_instruction
                    st.success("已儲存！")
            with col_del:
                if st.button("🗑️ 刪除"):
                    st.session_state['revisions'] = [item for item in st.session_state['revisions'] if item['id'] != selected_id]
                    st.rerun()
