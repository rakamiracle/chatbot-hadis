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
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# Main content
st.title("💬 Chat dengan Hadis")
st.caption("Tanyakan tentang hadis yang telah diupload")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "sources" in message:
            with st.expander("📚 Lihat Sumber"):
                for i, src in enumerate(message["sources"], 1):
                    st.markdown(f"**Sumber {i}** (Halaman {src['page_number']}, Similarity: {src['similarity_score']:.2f})")
                    st.text(src['text'])
                    st.markdown("---")

# Chat input
if prompt := st.chat_input("Tanyakan tentang hadis..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban..."):
            try:
                response = requests.post(
                    f"{API_URL}/chat/",
                    json={"query": prompt, "session_id": st.session_state.session_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    sources = data["sources"]
                    
                    st.markdown(answer)
                    
                    # Save to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                    
                    # Show sources
                    with st.expander("📚 Lihat Sumber"):
                        for i, src in enumerate(sources, 1):
                            st.markdown(f"**Sumber {i}** (Halaman {src['page_number']}, Similarity: {src['similarity_score']:.2f})")
                            st.text(src['text'])
                            st.markdown("---")
                else:
                    error_msg = f"Error {response.status_code}: {response.text}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            
            except Exception as e:
                error_msg = f"Gagal menghubungi server: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Footer
st.markdown("---")
st.caption("Chatbot Hadis v1.0 | Powered by Mistral & pgvector")
