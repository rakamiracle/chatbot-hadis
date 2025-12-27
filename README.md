# 📖 Chatbot Hadis

Chatbot berbasis RAG (Retrieval-Augmented Generation) untuk menjawab pertanyaan tentang hadis menggunakan vector similarity search dan LLM.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)
![Ollama](https://img.shields.io/badge/Ollama-Mistral-orange.svg)

---

## ✨ Fitur Utama

- 🔍 **Vector Similarity Search** dengan pgvector
- 🤖 **LLM Integration** menggunakan Ollama (Mistral)
- 📤 **PDF Upload** dengan automatic chunking dan embedding
- 💬 **Chat Interface** interaktif dengan Streamlit
- 📊 **Analytics Dashboard** untuk monitoring usage dan performance
- 🎯 **Filter Kitab** untuk pencarian lebih spesifik
- 🔤 **Auto-detect Arabic Text** dalam hasil pencarian
- 👍👎 **User Feedback System** untuk improve quality
- ⚡ **Performance Optimized** dengan caching dan batch processing

---

## 🏗️ Arsitektur

```
┌─────────────────┐
│  Streamlit UI   │ ← Frontend (Port 8501)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI       │ ← Backend API (Port 8000)
└────────┬────────┘
         │
    ┌────┴─────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ PostgreSQL │ Ollama │ Sentence│ PyMuPDF │
│ +pgvector  │ (LLM)  │Transform│  (PDF)  │
└────────┘ └────────┘ └────────┘ └────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ dengan pgvector extension
- Ollama dengan model Mistral
- Git

### Instalasi

#### Linux/Mac:

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/chatbot-hadis.git
cd chatbot-hadis

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Setup database
createdb chatbot_hadis
psql -d chatbot_hadis -c "CREATE EXTENSION vector;"
python scripts/setup_db.py

# Configure environment
cp .env.example .env
# Edit .env dengan konfigurasi Anda
```

#### Windows:

Lihat panduan lengkap di **[docs/WINDOWS_INSTALLATION_GUIDE.md](docs/WINDOWS_INSTALLATION_GUIDE.md)**

Atau quick checklist di **[docs/QUICK_SETUP_WINDOWS.md](docs/QUICK_SETUP_WINDOWS.md)**

### Jalankan Aplikasi

**Terminal 1 - Backend:**
```bash
python run.py
```

**Terminal 2 - Frontend:**
```bash
streamlit run streamlit_app.py
```

**Akses:**
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

---

## 📚 Dokumentasi

| Dokumen | Deskripsi |
|---------|-----------|
| [WINDOWS_INSTALLATION_GUIDE.md](docs/WINDOWS_INSTALLATION_GUIDE.md) | Panduan instalasi lengkap untuk Windows 10 |
| [QUICK_SETUP_WINDOWS.md](docs/QUICK_SETUP_WINDOWS.md) | Quick reference checklist untuk Windows |
| [OPTIMIZATION_GUIDE.md](docs/OPTIMIZATION_GUIDE.md) | Panduan optimasi performance |
| [ANALYTICS_GUIDE.md](docs/ANALYTICS_GUIDE.md) | Panduan analytics dan monitoring |
| [QUICK_START_OPTIMIZATION.md](docs/QUICK_START_OPTIMIZATION.md) | Quick tips optimasi |

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM untuk database
- **asyncpg** - Async PostgreSQL driver
- **pgvector** - Vector similarity search

### LLM & Embeddings
- **Ollama** - Local LLM runtime (Mistral)
- **sentence-transformers** - Text embeddings
- **PyTorch** - ML framework

### Frontend
- **Streamlit** - Interactive UI framework

### Database
- **PostgreSQL 16+** - Main database
- **pgvector extension** - Vector storage dan similarity search

### Utilities
- **PyMuPDF** - PDF text extraction
- **python-dotenv** - Environment configuration
- **loguru** - Logging
- **plotly** - Data visualization
- **pandas** - Data analysis

---

## 📁 Struktur Project

```
chatbot-hadis/
├── app/
│   ├── api/              # API routes
│   ├── database/         # Database connection & models
│   ├── models/           # SQLAlchemy models
│   ├── services/         # Business logic
│   └── utils/            # Utilities & helpers
├── docs/                 # Dokumentasi
├── scripts/              # Setup & maintenance scripts
├── tests/                # Unit tests
├── uploads/              # Uploaded PDF files
├── config.py             # Application configuration
├── run.py                # Backend entry point
├── streamlit_app.py      # Frontend entry point
├── requirements.txt      # Python dependencies
└── .env.example          # Environment variables template
```

---

## 🔧 Konfigurasi

File `.env` utama:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/chatbot_hadis

# LLM
OLLAMA_MODEL=mistral
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Application
APP_PORT=8000
SECRET_KEY=your-secret-key-here
TOP_K_RESULTS=5

# Performance
BATCH_SIZE=50
EMBEDDING_BATCH_SIZE=32
DB_POOL_SIZE=10
CACHE_TTL_MINUTES=30
```

Lihat [.env.example](.env.example) untuk konfigurasi lengkap dengan penjelasan.

---

## 📊 Database Schema

### Tables

- **hadis_documents** - Metadata dokumen PDF
- **hadis_chunks** - Text chunks dengan vector embeddings
- **chat_histories** - Riwayat percakapan
- **analytics_logs** - Logs untuk analytics
- **user_feedbacks** - Feedback dari user

### Vector Index

```sql
CREATE INDEX ON hadis_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## 🔍 API Endpoints

### Upload
- `POST /api/upload/` - Upload PDF hadis

### Chat
- `POST /api/chat/` - Kirim pertanyaan dan terima jawaban

### Documents
- `GET /api/documents/` - List semua dokumen
- `GET /api/documents/{id}` - Detail dokumen
- `GET /api/documents/kitab/list` - List semua kitab

### Analytics
- `POST /api/analytics/feedback` - Submit user feedback
- `GET /api/analytics/stats` - Get analytics statistics

Lihat lengkap di: http://localhost:8000/docs

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run dengan coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_embedding_service.py
```

---

## 📈 Performance Tips

1. **Vector Index**: Pastikan ada index di `hadis_chunks.embedding`
2. **Database Pool**: Sesuaikan `DB_POOL_SIZE` dengan beban
3. **Batch Processing**: Gunakan `BATCH_SIZE` yang optimal
4. **Caching**: Enable cache dengan `CACHE_TTL_MINUTES`
5. **Ollama**: Jalankan di GPU untuk performance lebih baik

Lihat [OPTIMIZATION_GUIDE.md](docs/OPTIMIZATION_GUIDE.md) untuk detail.

---

## 🐛 Troubleshooting

### Database Connection Error
```bash
# Cek PostgreSQL running
sudo systemctl status postgresql  # Linux
# atau
services.msc  # Windows (cari postgresql service)

# Cek pgvector extension
psql -d chatbot_hadis -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Ollama Connection Error
```bash
# Start Ollama
ollama serve

# Cek model tersedia
ollama list

# Pull model jika belum ada
ollama pull mistral
```

### Import Error
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

Lihat troubleshooting lengkap di [WINDOWS_INSTALLATION_GUIDE.md](docs/WINDOWS_INSTALLATION_GUIDE.md#troubleshooting)

---

## 🤝 Contributing

1. Fork repository
2. Buat branch feature (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push ke branch (`git push origin feature/AmazingFeature`)
5. Buka Pull Request

---

## 📝 License

This project is licensed under the MIT License.

---

## 👨‍💻 Developer

Dikembangkan dengan ❤️ untuk memudahkan pencarian dan pembelajaran hadis.

---

## 🔗 Links

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [Ollama](https://ollama.com/)
- [Sentence Transformers](https://www.sbert.net/)

---

## ⭐ Support

Jika project ini bermanfaat, berikan ⭐ di GitHub!

**Selamat menggunakan Chatbot Hadis!** 🎉
