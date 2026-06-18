import streamlit as st
import requests
import uuid

# Config
API_URL = "http://localhost:8000/api"

st.set_page_config(page_title="Chatbot Hadis", page_icon="📖", layout="wide")

# Custom CSS untuk fix layout
st.markdown("""
<style>
    /* Fix untuk teks Arab yang kepotong */
    .arabic-text {
        direction: rtl;
        font-size: 20px;
        line-height: 2;
        padding: 20px;
        background: linear-gradient(135deg, #f5f5f5 0%, #fafafa 100%);
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        word-wrap: break-word;
        overflow-wrap: break-word;
        white-space: normal;
        width: 100%;
        box-sizing: border-box;
        font-family: 'Arial', 'Segoe UI', sans-serif;
    }
    
    /* Fix untuk source metadata */
    .source-header {
        background: linear-gradient(90deg, #ff6b6b 0%, #ee5a6f 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 10px 0;
        font-weight: 500;
        word-wrap: break-word;
    }
    
    .source-content {
        background: #f9f9f9;
        padding: 16px;
        border-left: 4px solid #ff6b6b;
        border-radius: 4px;
        margin: 10px 0;
        word-wrap: break-word;
        white-space: normal;
    }
    
    /* Fix untuk ekspander */
    .streamlit-expanderHeader {
        background-color: #fff4f4;
        border-radius: 4px;
    }
    
    /* Fix untuk chat message */
    .chat-content {
        word-wrap: break-word;
        overflow-wrap: break-word;
        white-space: normal;
    }
    
    /* Fix untuk button feedback */
    .feedback-buttons {
        display: flex;
        gap: 10px;
        margin-top: 10px;
    }
    
    /* Improve disclaimer styling */
    .disclaimer-warning {
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 6px;
        padding: 12px;
        margin: 15px 0;
        color: #856404;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "kitab_filter" not in st.session_state:
    st.session_state.kitab_filter = None

# Sidebar
with st.sidebar:
    st.title("📖 Chatbot Hadis")
    st.markdown("---")
    
    st.subheader("Upload Dokumen PDF")
    uploaded_file = st.file_uploader("Pilih file PDF hadis", type=['pdf'])
    
    if uploaded_file:
        if st.button("Upload & Proses", use_container_width=True):
            with st.spinner("Memproses PDF..."):
                files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                try:
                    response = requests.post(f"{API_URL}/upload/", files=files)
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ {data['filename']} berhasil diupload!")
                        st.info(f"Total halaman: {data.get('total_pages', 'N/A')}")
                    else:
                        st.error(f"❌ Error: {response.text}")
                except Exception as e:
                    st.error(f"❌ Gagal upload: {str(e)}")

    st.markdown("---")
    st.subheader("📚 Filter Dokumen")

    try:
        kitab_response = requests.get(f"{API_URL}/documents/kitab/list")
        if kitab_response.status_code == 200:
            kitab_data = kitab_response.json()
            kitab_list = ["Semua Kitab"] + [k['kitab'] for k in kitab_data['kitab'] if k['kitab']]
            
            selected_kitab = st.selectbox("Pilih Kitab", kitab_list)
            
            if selected_kitab != "Semua Kitab":
                st.session_state.kitab_filter = selected_kitab
            else:
                st.session_state.kitab_filter = None
        else:
            st.session_state.kitab_filter = None
    except:
        st.session_state.kitab_filter = None

    st.markdown("---")
    st.subheader("⚙️ Pengaturan Tampilan")

    show_arabic = st.radio(
        "Tampilan Teks Arab",
        ["Auto (Deteksi Otomatis)", "Selalu Tampilkan", "Jangan Tampilkan"],
        help="Atur kapan teks Arab ditampilkan"
    )

    st.session_state.arabic_display_mode = show_arabic

    st.markdown("---")
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        # Clear local messages
        st.session_state.messages = []
        
        # ✅ TAMBAHAN: Clear backend cache untuk session ini
        old_session_id = st.session_state.session_id
        try:
            response = requests.post(
                f"{API_URL}/chat/clear-session-cache",
                json={"session_id": old_session_id},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                st.toast(f"✅ Cache dihapus ({data.get('cleared_entries', 0)} entries)", icon="✅")
            else:
                st.toast("⚠️ Gagal menghapus cache backend", icon="⚠️")
        except Exception as e:
            # Ignore jika backend tidak tersedia
            st.toast(f"⚠️ Backend tidak tersedia: {str(e)[:50]}", icon="⚠️")
        
        # Generate new session ID
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# Main content
st.title("💬 Chat dengan Hadis")
st.caption("Tanyakan tentang hadis yang telah diupload")

# Display chat messages
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(f"<div class='chat-content'>{message['content']}</div>", unsafe_allow_html=True)
        
        # Show sources if available
        if message["role"] == "assistant" and "sources" in message and len(message["sources"]) > 0:
            show_arabic_default = message.get("include_arabic", False)
            
            with st.expander("📚 Lihat Sumber Hadis", expanded=False):
                for i, src in enumerate(message["sources"], 1):
                    # Header dengan metadata
                    header_parts = []
                    
                    kitab = src.get('kitab_metadata') or src.get('kitab_name')
                    if kitab:
                        header_parts.append(f"📚 {kitab}")
                    
                    if src.get('bab'):
                        bab_text = f"Bab"
                        if src.get('bab_nomor'):
                            bab_text += f" {src['bab_nomor']}"
                        bab_text += f": {src['bab']}"
                        header_parts.append(bab_text)
                    
                    if src.get('hadis_number'):
                        header_parts.append(f"Hadis No. {src['hadis_number']}")
                    
                    if src.get('perawi'):
                        header_parts.append(f"HR. {src['perawi']}")
                    
                    if src.get('derajat'):
                        header_parts.append(f"({src['derajat']})")
                    
                    header_parts.append(f"Hal. {src['page_number']}")
                    header_parts.append(f"Sim: {src['similarity_score']:.2f}")
                    
                    header_html = " | ".join(header_parts)
                    st.markdown(f"<div class='source-header'>{header_html}</div>", unsafe_allow_html=True)
                    
                    # Arabic text (jika ada)
                    import re
                    text = src['text']
                    has_arabic_in_text = bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text))
                    
                    arabic_text = src.get('arabic_text') or (text if has_arabic_in_text else None)
                    if arabic_text:
                        # Determine initial state
                        initial_expand = show_arabic_default or (st.session_state.arabic_display_mode == "Selalu Tampilkan")
                        hide_arabic = st.session_state.arabic_display_mode == "Jangan Tampilkan"
                        
                        if not hide_arabic:
                            with st.expander("🔤 Teks Arab", expanded=initial_expand):
                                st.markdown(f"<div class='arabic-text'>{arabic_text}</div>", unsafe_allow_html=True)
                    
                    # Translation/text
                    if not has_arabic_in_text or (has_arabic_in_text and arabic_text != text):
                        st.markdown("**📝 Terjemahan/Penjelasan:**")
                        st.markdown(f"<div class='source-content'>{text}</div>", unsafe_allow_html=True)
                    
                    st.markdown("")
        
        # Show feedback buttons
        if message["role"] == "assistant":
            feedback_key = f"feedback_{idx}"
            if feedback_key not in st.session_state:
                st.session_state[feedback_key] = None
            
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button("👍", key=f"thumbs_up_{idx}", help="Jawaban membantu"):
                    st.session_state[feedback_key] = "thumbs_up"
                    try:
                        feedback_data = {
                            "session_id": st.session_state.session_id,
                            "query": message.get("query", ""),
                            "response": message["content"],
                            "feedback_type": "thumbs_up",
                            "chunks_count": len(message.get("sources", []))
                        }
                        response = requests.post(f"{API_URL}/analytics/feedback", json=feedback_data)
                        if response.status_code == 200:
                            st.toast("✅ Terima kasih atas feedback Anda!", icon="✅")
                    except Exception as e:
                        st.toast(f"❌ Gagal mengirim feedback: {e}", icon="❌")
            
            with col2:
                if st.button("👎", key=f"thumbs_down_{idx}", help="Jawaban kurang membantu"):
                    st.session_state[feedback_key] = "thumbs_down"
                    try:
                        feedback_data = {
                            "session_id": st.session_state.session_id,
                            "query": message.get("query", ""),
                            "response": message["content"],
                            "feedback_type": "thumbs_down",
                            "chunks_count": len(message.get("sources", []))
                        }
                        response = requests.post(f"{API_URL}/analytics/feedback", json=feedback_data)
                        if response.status_code == 200:
                            st.toast("📝 Terima kasih! Kami akan terus meningkatkan kualitas jawaban.", icon="ℹ️")
                    except Exception as e:
                        st.toast(f"❌ Gagal mengirim feedback: {e}", icon="❌")

# Chat input
if prompt := st.chat_input("Tanyakan tentang hadis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(f"<div class='chat-content'>{prompt}</div>", unsafe_allow_html=True)
    
    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban..."):
            try:
                payload = {
                    "query": prompt,
                    "session_id": st.session_state.session_id
                }
                
                if hasattr(st.session_state, 'kitab_filter') and st.session_state.kitab_filter:
                    payload["kitab_filter"] = st.session_state.kitab_filter
                
                if hasattr(st.session_state, 'arabic_display_mode'):
                    if st.session_state.arabic_display_mode == "Selalu Tampilkan":
                        payload["force_arabic"] = True
                    elif st.session_state.arabic_display_mode == "Jangan Tampilkan":
                        payload["force_arabic"] = False
                
                response = requests.post(f"{API_URL}/chat/", json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    sources = data["sources"]
                    include_arabic = data.get("include_arabic", False)
                    
                    # Tampilkan jawaban dengan format yang lebih baik
                    st.markdown(f"<div class='chat-content'>{answer}</div>", unsafe_allow_html=True)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "include_arabic": include_arabic,
                        "query": prompt
                    })
                    
                    # Display sources
                    if sources:
                        with st.expander("📚 Lihat Sumber Hadis", expanded=False):
                            for i, src in enumerate(sources, 1):
                                header_parts = []
                                
                                kitab = src.get('kitab_metadata') or src.get('kitab_name')
                                if kitab:
                                    header_parts.append(f"📚 {kitab}")
                                
                                if src.get('bab'):
                                    bab_text = f"Bab"
                                    if src.get('bab_nomor'):
                                        bab_text += f" {src['bab_nomor']}"
                                    bab_text += f": {src['bab']}"
                                    header_parts.append(bab_text)
                                
                                if src.get('hadis_number'):
                                    header_parts.append(f"Hadis No. {src['hadis_number']}")
                                
                                if src.get('perawi'):
                                    header_parts.append(f"HR. {src['perawi']}")
                                
                                if src.get('derajat'):
                                    header_parts.append(f"({src['derajat']})")
                                
                                header_parts.append(f"Hal. {src['page_number']}")
                                header_parts.append(f"Sim: {src['similarity_score']:.2f}")
                                
                                header_html = " | ".join(header_parts)
                                st.markdown(f"<div class='source-header'>{header_html}</div>", unsafe_allow_html=True)
                                
                                # Check for Arabic
                                import re
                                text = src['text']
                                has_arabic_in_text = bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text))
                                
                                arabic_text = src.get('arabic_text') or (text if has_arabic_in_text else None)
                                if arabic_text:
                                    initial_expand = include_arabic or (st.session_state.arabic_display_mode == "Selalu Tampilkan")
                                    hide_arabic = st.session_state.arabic_display_mode == "Jangan Tampilkan"
                                    
                                    if not hide_arabic:
                                        with st.expander("🔤 Teks Arab", expanded=initial_expand):
                                            st.markdown(f"<div class='arabic-text'>{arabic_text}</div>", unsafe_allow_html=True)
                                
                                if not has_arabic_in_text or (has_arabic_in_text and arabic_text != text):
                                    st.markdown("**📝 Terjemahan/Penjelasan:**")
                                    st.markdown(f"<div class='source-content'>{text}</div>", unsafe_allow_html=True)
                                
                                st.markdown("")
                else:
                    err = f"Error {response.status_code}: {response.text}"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})
            
            except Exception as e:
                err = f"Gagal menghubungi server: {str(e)}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})

        # Debug Panel (Opsional - bisa di-comment jika tidak perlu)
with st.sidebar:
    st.markdown("---")
    with st.expander("🔧 Debug Info", expanded=False):
        st.caption(f"Session ID: {st.session_state.session_id[:8]}...")
        
        # Get cache stats
        try:
            stats_response = requests.get(f"{API_URL}/chat/cache-stats", timeout=3)
            if stats_response.status_code == 200:
                stats = stats_response.json()['stats']
                st.metric("Total Cache Entries", stats['total_entries'])
                st.metric("Embedding Cache", stats['embedding_cache'])
                st.metric("Results Cache", stats['results_cache'])
                st.metric("Cache TTL (minutes)", stats['ttl_minutes'])
            else:
                st.caption("Cache stats tidak tersedia")
        except:
            st.caption("Backend tidak tersedia")
        
        if st.button("🔄 Force Clear All Cache", use_container_width=True):
            try:
                requests.post(f"{API_URL}/chat/clear-cache")
                st.success("✅ All cache cleared!")
                st.rerun()
            except:
                st.error("❌ Failed to clear cache")
# Footer
st.markdown("---")
st.caption("Chatbot Hadis v2.0 | Improved Layout & Complete Answers | Powered by Mistral & pgvector")