# ⚡ Quick Setup Checklist - Windows 10

Checklist singkat untuk setup Chatbot Hadis di Windows 10.

> **Panduan lengkap**: Lihat [WINDOWS_INSTALLATION_GUIDE.md](./WINDOWS_INSTALLATION_GUIDE.md)

---

## ✅ Checklist Instalasi

### 1️⃣ Install Prerequisites

- [ ] **Python 3.12+** - https://www.python.org/downloads/
  - ⚠️ Jangan lupa centang "Add Python to PATH"
  - Verifikasi: `python --version`

- [ ] **PostgreSQL 16+** - https://www.postgresql.org/download/windows/
  - Catat password user `postgres`
  - Port: `5432`
  - Verifikasi: `psql -U postgres`

- [ ] **pgvector Extension** untuk PostgreSQL
  - Download dari: https://github.com/pgvector/pgvector/releases
  - Copy `vector.dll` ke `C:\Program Files\PostgreSQL\16\lib`
  - Copy `vector.control` dan `vector--*.sql` ke `C:\Program Files\PostgreSQL\16\share\extension`

- [ ] **Git** - https://git-scm.com/download/win
  - Verifikasi: `git --version`

- [ ] **Ollama** - https://ollama.com/download
  - Download model: `ollama pull mistral`
  - Verifikasi: `ollama list`

---

### 2️⃣ Setup Project

```cmd
# Clone repository
cd C:\Users\%USERNAME%\Documents
mkdir Projects
cd Projects
git clone https://github.com/YOUR_USERNAME/chatbot-hadis.git
cd chatbot-hadis

# Buat virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 3️⃣ Konfigurasi

**Buat file `.env`:**

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/chatbot_hadis
OLLAMA_MODEL=mistral
EMBEDDING_MODEL=all-MiniLM-L6-v2
APP_PORT=8000
SECRET_KEY=your-secret-key-change-this-min-32-chars
UPLOAD_DIR=uploads
TOP_K_RESULTS=5
BATCH_SIZE=50
EMBEDDING_BATCH_SIZE=32
DB_POOL_SIZE=10
CACHE_TTL_MINUTES=30
```

> Ganti `YOUR_PASSWORD` dengan password PostgreSQL Anda!

---

### 4️⃣ Setup Database

```cmd
# Buat database
psql -U postgres
```

```sql
CREATE DATABASE chatbot_hadis;
\c chatbot_hadis
CREATE EXTENSION vector;
\q
```

```cmd
# Inisialisasi tables
python scripts/setup_db.py
```

---

### 5️⃣ Jalankan Aplikasi

**Terminal 1 - Backend:**
```cmd
cd C:\Users\%USERNAME%\Documents\Projects\chatbot-hadis
venv\Scripts\activate
python run.py
```

**Terminal 2 - Frontend:**
```cmd
cd C:\Users\%USERNAME%\Documents\Projects\chatbot-hadis
venv\Scripts\activate
streamlit run streamlit_app.py
```

**Akses:**
- Frontend: http://localhost:8501
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🚀 Quick Start Scripts (Opsional)

**Buat `start_backend.bat`:**
```bat
@echo off
cd C:\Users\%USERNAME%\Documents\Projects\chatbot-hadis
call venv\Scripts\activate
python run.py
pause
```

**Buat `start_frontend.bat`:**
```bat
@echo off
cd C:\Users\%USERNAME%\Documents\Projects\chatbot-hadis
call venv\Scripts\activate
streamlit run streamlit_app.py
pause
```

Double-click file `.bat` untuk quick start!

---

## ⚠️ Common Issues

| Error | Solusi |
|-------|--------|
| `asyncpg connection failed` | Cek PostgreSQL service running di `services.msc` |
| `vector extension not found` | Install pgvector, lalu `CREATE EXTENSION vector;` |
| `Ollama connection refused` | Jalankan `ollama serve` |
| `torch installation failed` | `pip install torch --index-url https://download.pytorch.org/whl/cu118` |
| `venv\Scripts\activate` error | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |

---

## 📋 Verifikasi Instalasi

Pastikan semua perintah ini berhasil:

```cmd
python --version          # Python 3.12.x
pip --version             # pip 24.x
git --version             # git 2.x
psql --version            # psql 16.x
ollama list               # mistral ada di list
```

---

**Next Steps**: Upload PDF hadis → Chat → Lihat hasilnya! 🎉
