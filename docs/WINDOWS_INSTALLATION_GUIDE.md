# 🪟 Panduan Instalasi Chatbot Hadis di Windows 10

Panduan lengkap untuk menginstall dan menjalankan project **Chatbot Hadis** dari nol di komputer Windows 10.

---

## 📋 Daftar Isi

1. [Prerequisites yang Harus Diinstall](#prerequisites-yang-harus-diinstall)
2. [Langkah 1: Install Python](#langkah-1-install-python)
3. [Langkah 2: Install PostgreSQL](#langkah-2-install-postgresql)
4. [Langkah 3: Install Git](#langkah-3-install-git)
5. [Langkah 4: Install Ollama](#langkah-4-install-ollama)
6. [Langkah 5: Clone Repository](#langkah-5-clone-repository)
7. [Langkah 6: Setup Virtual Environment](#langkah-6-setup-virtual-environment)
8. [Langkah 7: Konfigurasi Environment Variables](#langkah-7-konfigurasi-environment-variables)
9. [Langkah 8: Setup Database](#langkah-8-setup-database)
10. [Langkah 9: Jalankan Aplikasi](#langkah-9-jalankan-aplikasi)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites yang Harus Diinstall

Berikut adalah software yang perlu Anda install di komputer Windows 10 Anda:

| Software | Versi Minimum | Fungsi |
|----------|---------------|--------|
| **Python** | 3.10+ | Runtime untuk menjalankan aplikasi |
| **PostgreSQL** | 14+ | Database dengan extension pgvector |
| **Git** | 2.x | Version control untuk clone repository |
| **Ollama** | Latest | LLM runtime untuk model Mistral |

---

## Langkah 1: Install Python

### 1.1 Download Python

1. Buka browser dan kunjungi: https://www.python.org/downloads/
2. Download **Python 3.12.x** (atau versi 3.10+ terbaru)
3. Pilih installer **Windows installer (64-bit)**

### 1.2 Install Python

1. Jalankan installer yang sudah didownload
2. **PENTING**: ✅ Centang **"Add Python to PATH"**
3. Klik **"Install Now"**
4. Tunggu proses instalasi selesai

### 1.3 Verifikasi Instalasi

Buka **Command Prompt** (tekan `Win + R`, ketik `cmd`, Enter) dan jalankan:

```cmd
python --version
```

Harusnya muncul output seperti:
```
Python 3.12.x
```

```cmd
pip --version
```

Harusnya muncul output seperti:
```
pip 24.x from ...
```

---

## Langkah 2: Install PostgreSQL

### 2.1 Download PostgreSQL

1. Kunjungi: https://www.postgresql.org/download/windows/
2. Klik **"Download the installer"** dari EnterpriseDB
3. Download versi **PostgreSQL 16.x** (64-bit)

### 2.2 Install PostgreSQL

1. Jalankan installer
2. Ikuti wizard instalasi:
   - **Installation Directory**: Biarkan default (`C:\Program Files\PostgreSQL\16`)
   - **Select Components**: Pilih semua (PostgreSQL Server, pgAdmin 4, Stack Builder, Command Line Tools)
   - **Data Directory**: Biarkan default
   - **Password**: Buat password untuk user `postgres` (CATAT PASSWORD INI!)
   - **Port**: Biarkan default `5432`
   - **Locale**: Default
3. Klik **Next** sampai selesai

### 2.3 Install Extension pgvector

1. Buka **Command Prompt** sebagai Administrator
2. Download dan install pgvector:

```cmd
cd C:\Program Files\PostgreSQL\16\bin
```

**Opsi A: Compile dari Source (Butuh Visual Studio)**

Jika Anda tidak familiar dengan compile, lanjut ke **Opsi B**.

**Opsi B: Download Pre-compiled Binary**

1. Kunjungi: https://github.com/pgvector/pgvector/releases
2. Download file `pgvector-0.x.x-windows.zip`
3. Extract file tersebut
4. Copy file `vector.dll` ke `C:\Program Files\PostgreSQL\16\lib`
5. Copy file `vector.control` dan `vector--*.sql` ke `C:\Program Files\PostgreSQL\16\share\extension`

### 2.4 Verifikasi PostgreSQL

Buka **Command Prompt** dan jalankan:

```cmd
psql -U postgres -p 5432
```

Masukkan password yang Anda buat tadi. Jika berhasil login, ketik:

```sql
\q
```

untuk keluar.

---

## Langkah 3: Install Git

### 3.1 Download Git

1. Kunjungi: https://git-scm.com/download/win
2. Download installer **64-bit Git for Windows Setup**

### 3.2 Install Git

1. Jalankan installer
2. Ikuti wizard dengan pengaturan default
3. Klik **Next** sampai selesai

### 3.3 Verifikasi Git

Buka **Command Prompt** baru dan jalankan:

```cmd
git --version
```

Harusnya muncul:
```
git version 2.x.x
```

---

## Langkah 4: Install Ollama

### 4.1 Download Ollama

1. Kunjungi: https://ollama.com/download
2. Klik **Download for Windows**

### 4.2 Install Ollama

1. Jalankan installer `OllamaSetup.exe`
2. Ikuti wizard instalasi
3. Ollama akan otomatis running di background

### 4.3 Download Model Mistral

Buka **Command Prompt** dan jalankan:

```cmd
ollama pull mistral
```

Tunggu proses download selesai (ukuran ~4GB).

### 4.4 Verifikasi Ollama

```cmd
ollama list
```

Harusnya muncul model `mistral` di daftar.

---

## Langkah 5: Clone Repository

### 5.1 Buat Folder Project

Buka **Command Prompt** dan jalankan:

```cmd
cd C:\Users\%USERNAME%\Documents
mkdir Projects
cd Projects
```

### 5.2 Clone dari GitHub

```cmd
git clone https://github.com/YOUR_USERNAME/chatbot-hadis.git
cd chatbot-hadis
```

> **Catatan**: Ganti `YOUR_USERNAME` dengan username GitHub Anda.

---

## Langkah 6: Setup Virtual Environment

### 6.1 Buat Virtual Environment

Di dalam folder `chatbot-hadis`, jalankan:

```cmd
python -m venv venv
```

### 6.2 Aktivasi Virtual Environment

```cmd
venv\Scripts\activate
```

Setelah aktivasi, prompt akan berubah menjadi:
```
(venv) C:\Users\...\chatbot-hadis>
```

### 6.3 Install Dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

Proses ini akan memakan waktu 5-15 menit tergantung kecepatan internet (download PyTorch, sentence-transformers, dll).

> **Troubleshooting**: Jika ada error saat install PyTorch di Windows, coba:
> ```cmd
> pip install torch --index-url https://download.pytorch.org/whl/cu118
> ```

---

## Langkah 7: Konfigurasi Environment Variables

### 7.1 Buat File .env

Di dalam folder `chatbot-hadis`, buat file baru bernama `.env` (tanpa ekstensi).

**Cara termudah menggunakan Notepad:**

```cmd
notepad .env
```

Klik **Yes** jika ditanya "Do you want to create a new file?"

### 7.2 Isi File .env

Copy dan paste konfigurasi berikut ke dalam file `.env`:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD_ANDA@localhost:5432/chatbot_hadis

# Ollama Configuration
OLLAMA_MODEL=mistral
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Application Settings
APP_PORT=8000
SECRET_KEY=your-secret-key-change-this-in-production-min-32-chars

# Upload Settings
UPLOAD_DIR=uploads

# Performance Settings
TOP_K_RESULTS=5
BATCH_SIZE=50
EMBEDDING_BATCH_SIZE=32
DB_POOL_SIZE=10
CACHE_TTL_MINUTES=30
```

> **PENTING**: Ganti `PASSWORD_ANDA` dengan password PostgreSQL yang Anda buat di Langkah 2.

### 7.3 Simpan File

Tekan `Ctrl + S` untuk save, lalu tutup Notepad.

---

## Langkah 8: Setup Database

### 8.1 Buat Database

Buka **Command Prompt** dan jalankan:

```cmd
psql -U postgres
```

Masukkan password PostgreSQL Anda. Lalu jalankan SQL berikut:

```sql
CREATE DATABASE chatbot_hadis;
\c chatbot_hadis
CREATE EXTENSION vector;
\q
```

### 8.2 Inisialisasi Tables

Kembali ke folder project (pastikan virtual environment aktif), jalankan:

```cmd
python scripts/setup_db.py
```

Harusnya muncul output:
```
✓ Database ready
```

### 8.3 (Opsional) Import Data dari MySQL

Jika Anda punya data hadis di MySQL, jalankan:

```cmd
python scripts/import_from_mysql.py
```

Pastikan Anda sudah configure MySQL connection di script tersebut.

### 8.4 (Opsional) Generate Embeddings

Jika sudah import data, generate embeddings:

```cmd
python scripts/add_document_embeddings.py
```

---

## Langkah 9: Jalankan Aplikasi

### 9.1 Jalankan Backend (FastAPI)

Buka **Command Prompt** pertama, aktifkan venv, dan jalankan:

```cmd
cd C:\Users\%USERNAME%\Documents\Projects\chatbot-hadis
venv\Scripts\activate
python run.py
```

Harusnya muncul:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
✓ Database initialized
✓ Embedding model warmed up
```

**Jangan tutup window ini!**

### 9.2 Jalankan Frontend (Streamlit)

Buka **Command Prompt** kedua (window baru), aktifkan venv, dan jalankan:

```cmd
cd C:\Users\%USERNAME%\Documents\Projects\chatbot-hadis
venv\Scripts\activate
streamlit run streamlit_app.py
```

Harusnya browser akan otomatis terbuka ke `http://localhost:8501`

### 9.3 Akses Aplikasi

- **Frontend (Streamlit)**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 🎉 Selesai!

Aplikasi Chatbot Hadis sudah running di komputer Windows 10 Anda!

### Langkah Selanjutnya:

1. **Upload PDF Hadis** melalui sidebar di Streamlit
2. **Tanya Hadis** melalui chat interface
3. **Lihat Analytics** (jika sudah import data)

---

## Troubleshooting

### ❌ Error: "psycopg2" not installed

**Solusi**:
```cmd
pip install psycopg2-binary
```

### ❌ Error: "asyncpg" connection failed

**Penyebab**: PostgreSQL tidak running atau password salah

**Solusi**:
1. Buka **Services** (tekan `Win + R`, ketik `services.msc`)
2. Cari service **postgresql-x64-16**
3. Klik kanan → **Start** jika statusnya Stopped
4. Periksa password di file `.env`

### ❌ Error: "vector extension not found"

**Solusi**:
1. Pastikan pgvector sudah terinstall (Langkah 2.3)
2. Reconnect ke database:
   ```cmd
   psql -U postgres -d chatbot_hadis
   CREATE EXTENSION vector;
   ```

### ❌ Error: "Ollama connection refused"

**Solusi**:
1. Pastikan Ollama running:
   ```cmd
   ollama serve
   ```
2. Di Command Prompt lain, cek model:
   ```cmd
   ollama list
   ```

### ❌ Error: "torch" installation failed on Windows

**Solusi**:
```cmd
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### ❌ Port 8000 atau 8501 sudah dipakai

**Solusi**:
1. Cek process yang pakai port:
   ```cmd
   netstat -ano | findstr :8000
   ```
2. Kill process:
   ```cmd
   taskkill /PID <PID_NUMBER> /F
   ```
3. Atau ubah port di `.env` (APP_PORT) atau streamlit config

### ❌ Virtual environment tidak bisa diaktifasi

**Solusi**:

Jika muncul error execution policy:
```cmd
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Lalu coba lagi:
```cmd
venv\Scripts\activate
```

---

## 📞 Butuh Bantuan?

Jika mengalami masalah yang tidak tercantum di sini:

1. Periksa log error di Command Prompt
2. Buka **GitHub Issues** di repository
3. Sertakan:
   - Versi Python: `python --version`
   - Versi PostgreSQL: `psql --version`
   - Error message lengkap
   - Output dari `pip list`

---

## 📝 Catatan Penting

### Setiap kali restart komputer:

1. **PostgreSQL** biasanya auto-start sebagai service
2. **Ollama** perlu dijalankan manual atau set sebagai startup service
3. **Virtual environment** harus diaktifkan ulang setiap buka Command Prompt baru

### Cara cepat untuk development:

Buat file `start_backend.bat`:
```bat
@echo off
cd C:\Users\%USERNAME%\Documents\Projects\chatbot-hadis
call venv\Scripts\activate
python run.py
pause
```

Buat file `start_frontend.bat`:
```bat
@echo off
cd C:\Users\%USERNAME%\Documents\Projects\chatbot-hadis
call venv\Scripts\activate
streamlit run streamlit_app.py
pause
```

Double-click file `.bat` tersebut untuk quick start!

---

## 🔐 Security Checklist untuk Production

Jika deploy ke server production:

- [ ] Ganti `SECRET_KEY` dengan random string 32+ karakter
- [ ] Ganti password PostgreSQL default
- [ ] Setup firewall untuk port 5432, 8000, 8501
- [ ] Gunakan HTTPS untuk frontend
- [ ] Batasi CORS di `app/main.py`
- [ ] Gunakan environment variables yang aman (bukan file `.env`)
- [ ] Setup backup database secara regular

---
 j
**Dibuat**: 2025-12-16  
**Versi**: 1.0  
**Project**: Chatbot Hadis v1.0
