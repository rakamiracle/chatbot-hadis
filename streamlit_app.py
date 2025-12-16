import streamlit as st
import requests
import uuid

# Config
API_URL = "http://localhost:8000/api"

st.set_page_config(page_title="Chatbot Hadis", page_icon="📖", layout="wide")

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

    # ==========================
    # 🔥 CODE BARU: Filter Dokumen
    # ==========================
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
    # ==========================
    # 🔥 END CODE BARU
    # ==========================

    # ==========================
    # ⚙️ Pengaturan Tampilan
    # ==========================
    st.markdown("---")
    st.subheader("⚙️ Pengaturan Tampilan")

    # Toggle untuk force show/hide Arab
    show_arabic = st.radio(
        "Tampilan Teks Arab",
        ["Auto (Deteksi Otomatis)", "Selalu Tampilkan", "Jangan Tampilkan"],
        help="Atur kapan teks Arab ditampilkan"
    )

    st.session_state.arabic_display_mode = show_arabic
    # ==========================

    st.markdown("---")
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# Main content
st.title("💬 Chat dengan Hadis")
st.caption("Tanyakan tentang hadis yang telah diupload")

# Display chat messages
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Show sources if available
        if message["role"] == "assistant" and "sources" in message and len(message["sources"]) > 0:
            # Get include_arabic flag (default False for old messages)
            show_arabic_default = message.get("include_arabic", False)
            
            with st.expander("📚 Lihat Sumber Hadis"):
                for i, src in enumerate(message["sources"], 1):
                    # Header sumber
                    st.markdown(f"**📖 Sumber {i}** (Halaman {src['page_number']}, Similarity: {src['similarity_score']:.2f})")
                    
                    # Check if text contains Arabic characters
                    import re
                    text = src['text']
                    has_arabic_in_text = bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text))
                    
                    # Show Arabic text (from metadata or from text if text is Arabic)
                    arabic_text = src.get('arabic_text') or (text if has_arabic_in_text else None)
                    if arabic_text:
                        with st.expander("🔤 Lihat Teks Arab", expanded=show_arabic_default):
                            st.markdown(f"<div dir='rtl' style='font-size: 20px; line-height: 1.8; padding: 10px; background: #f5f5f5; border-radius: 8px; border: 1px solid #ddd;'>{arabic_text}</div>", unsafe_allow_html=True)
                    
                    # Show translation/text (only if not primarily Arabic)
                    if not has_arabic_in_text:
                        st.markdown("**📝 Teks:**")
                        st.text(text)
                    
                    # Info tambahan
                    if src.get('perawi'):
                        st.caption(f"👤 Perawi: {src['perawi']}")
                    if src.get('hadis_number'):
                        st.caption(f"🔢 Hadis #{src['hadis_number']}")
                    if src.get('kitab_name'):
                        st.caption(f"📚 Kitab: {src['kitab_name']}")
                    
                    st.markdown("---")
        
        # Show feedback buttons for all assistant messages
        if message["role"] == "assistant":
            # Add feedback buttons
            feedback_key = f"feedback_{idx}"
            if feedback_key not in st.session_state:
                st.session_state[feedback_key] = None
            
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button("👍", key=f"thumbs_up_{idx}", help="Jawaban membantu"):
                    st.session_state[feedback_key] = "thumbs_up"
                    # Send feedback to backend
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
                    # Send feedback to backend
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

# ======================================
# 🔥 INPUT BARU: Chat + Filter Kitab
# ======================================
if prompt := st.chat_input("Tanyakan tentang hadis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban..."):
            try:
                payload = {
                    "query": prompt,
                    "session_id": st.session_state.session_id
                }
                
                # Tambahkan filter jika ada
                if hasattr(st.session_state, 'kitab_filter') and st.session_state.kitab_filter:
                    payload["kitab_filter"] = st.session_state.kitab_filter
                
                # Tambahkan mode Arabic display
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
                    include_arabic = data.get("include_arabic", False)  # Get flag dari backend
                    
                    st.markdown(answer)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "include_arabic": include_arabic,  # Store flag
                        "query": prompt  # Store query for feedback
                    })
                    
                    with st.expander("📚 Lihat Sumber Hadis"):
                        for i, src in enumerate(sources, 1):
                            # Header sumber
                            st.markdown(f"**📖 Sumber {i}** (Halaman {src['page_number']}, Similarity: {src['similarity_score']:.2f})")
                            
                            # Check if text contains Arabic characters
                            import re
                            text = src['text']
                            has_arabic_in_text = bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text))
                            
                            # Show Arabic text (from metadata or from text if text is Arabic)
                            arabic_text = src.get('arabic_text') or (text if has_arabic_in_text else None)
                            if arabic_text:
                                with st.expander("🔤 Lihat Teks Arab", expanded=include_arabic):
                                    st.markdown(f"<div dir='rtl' style='font-size: 20px; line-height: 1.8; padding: 10px; background: #f5f5f5; border-radius: 8px; border: 1px solid #ddd;'>{arabic_text}</div>", unsafe_allow_html=True)
                            
                            # Show translation/text (only if not primarily Arabic)
                            if not has_arabic_in_text:
                                st.markdown("**📝 Teks:**")
                                st.text(text)
                            
                            # Info tambahan
                            if src.get('perawi'):
                                st.caption(f"👤 Perawi: {src['perawi']}")
                            if src.get('hadis_number'):
                                st.caption(f"🔢 Hadis #{src['hadis_number']}")
                            if src.get('kitab_name'):
                                st.caption(f"📚 Kitab: {src['kitab_name']}")
                            
                            st.markdown("---")
                else:
                    err = f"Error {response.status_code}: {response.text}"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})
            
            except Exception as e:
                err = f"Gagal menghubungi server: {str(e)}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
# ======================================
# 🔥 END INPUT BARU
# ======================================

# Footer
st.markdown("---")
st.caption("Chatbot Hadis v1.0 | Powered by Mistral & pgvector")
