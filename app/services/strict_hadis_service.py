# from typing import List, Dict, Optional
# from dataclasses import dataclass
# from enum import Enum

# class DerajatHadis(str, Enum):
#     """Derajat hadis yang diperbolehkan"""
#     SHAHIH = "Shahih"
#     HASAN = "Hasan"
#     DHAIF = "Dhaif"
#     MAUDHU = "Maudhu"  # ❌ Tidak akan ditampilkan

# @dataclass
# class HadisValidated:
#     """Struktur hadis yang sudah tervalidasi"""
#     id: str
#     terjemah: str
#     arab: Optional[str]
#     sumber: str
#     derajat: DerajatHadis
#     tema: List[str]
#     makna_singkat: Optional[str]
#     nomor_hadis: Optional[str]
#     kitab: Optional[str]
#     perawi: Optional[str]

# class HadisValidator:
#     """
#     Layer validasi WAJIB untuk semua hadis
#     Hadis harus lolos validasi sebelum ditampilkan
#     """
    
#     @staticmethod
#     def validate_hadis(chunk: Dict) -> Optional[HadisValidated]:
#         """
#         Validasi hadis dari database chunk
        
#         ✅ Wajib ada:
#         - terjemah / text
#         - sumber / perawi
#         - derajat
        
#         ❌ Reject:
#         - Hadis maudhu
#         - Tidak ada sumber
#         """
#         metadata = chunk.get('metadata', {})
#         text = chunk.get('text', '')
        
#         # Validasi 1: Harus ada text
#         if not text or len(text.strip()) < 10:
#             return None
        
#         # Validasi 2: Harus ada sumber (perawi atau kitab)
#         perawi = metadata.get('perawi')
#         kitab = metadata.get('kitab') or chunk.get('kitab_name')
        
#         if not perawi and not kitab:
#             return None  # ❌ Tidak ada sumber
        
#         sumber = f"HR. {perawi}" if perawi else kitab
        
#         # Validasi 3: Cek derajat
#         derajat_raw = metadata.get('derajat', 'Tidak diketahui')
#         derajat = HadisValidator._normalize_derajat(derajat_raw)
        
#         # ❌ REJECT hadis maudhu
#         if derajat == DerajatHadis.MAUDHU:
#             return None
        
#         # ✅ Build validated hadis
#         return HadisValidated(
#             id=str(chunk.get('chunk_id', '')),
#             terjemah=text,
#             arab=metadata.get('arab'),
#             sumber=sumber,
#             derajat=derajat,
#             tema=HadisValidator._extract_tema(metadata),
#             makna_singkat=None,  # Akan diisi dari database atau LLM terbatas
#             nomor_hadis=metadata.get('nomor_hadis'),
#             kitab=kitab,
#             perawi=perawi
#         )
    
#     @staticmethod
#     def _normalize_derajat(derajat_raw: str) -> DerajatHadis:
#         """Normalisasi derajat hadis"""
#         derajat_lower = derajat_raw.lower()
        
#         if 'shahih' in derajat_lower or 'sahih' in derajat_lower:
#             return DerajatHadis.SHAHIH
#         elif 'hasan' in derajat_lower:
#             return DerajatHadis.HASAN
#         elif 'dhaif' in derajat_lower or 'daif' in derajat_lower:
#             return DerajatHadis.DHAIF
#         elif 'maudhu' in derajat_lower or 'palsu' in derajat_lower:
#             return DerajatHadis.MAUDHU
        
#         return DerajatHadis.DHAIF  # Default sebagai dhaif (hati-hati)
    
#     @staticmethod
#     def _extract_tema(metadata: Dict) -> List[str]:
#         """Extract tema dari metadata"""
#         tema = []
        
#         if metadata.get('bab'):
#             tema.append(metadata['bab'])
        
#         if metadata.get('kitab'):
#             tema.append(metadata['kitab'])
        
#         return tema


# class StrictResponseFormatter:
#     """
#     🔐 TEMPLATE RESPONSE TERKUNCI
#     Format ini TIDAK BOLEH diubah oleh LLM
#     """
    
#     @staticmethod
#     def format_single_hadis(hadis: HadisValidated, include_makna: bool = True) -> str:
#         """
#         Format hadis tunggal dengan template ketat
        
#         Format:
#         ```
#         Hadis:
        
#         [Terjemah]
        
#         Sumber: HR. ...
#         Derajat: ...
        
#         Makna singkat:
#         [Penjelasan ringkas]
#         ```
#         """
#         response = "**Hadis:**\n\n"
        
#         # Terjemah
#         response += f"{hadis.terjemah}\n\n"
        
#         # Metadata
#         response += f"**Sumber:** {hadis.sumber}\n"
#         response += f"**Derajat:** {hadis.derajat.value}\n"
        
#         if hadis.nomor_hadis:
#             response += f"**No. Hadis:** {hadis.nomor_hadis}\n"
        
#         # Warning untuk hadis dhaif
#         if hadis.derajat == DerajatHadis.DHAIF:
#             response += "\n⚠️ **Catatan:** Hadis ini berstatus dhaif sehingga tidak dijadikan dalil utama.\n"
        
#         # Makna singkat (opsional)
#         if include_makna and hadis.makna_singkat:
#             response += f"\n**Makna singkat:**\n{hadis.makna_singkat}\n"
        
#         return response
    
#     @staticmethod
#     def format_multiple_hadis(hadis_list: List[HadisValidated], max_show: int = 3) -> str:
#         """Format beberapa hadis dengan separator"""
        
#         if not hadis_list:
#             return StrictResponseFormatter.format_not_found()
        
#         response = f"Ditemukan {len(hadis_list)} hadis terkait:\n\n"
#         response += "---\n\n"
        
#         for i, hadis in enumerate(hadis_list[:max_show], 1):
#             response += f"### Hadis {i}\n\n"
#             response += StrictResponseFormatter.format_single_hadis(hadis, include_makna=False)
#             response += "\n---\n\n"
        
#         if len(hadis_list) > max_show:
#             response += f"\n*Lihat {len(hadis_list) - max_show} hadis lainnya di sumber.*\n"
        
#         return response
    
#     @staticmethod
#     def format_not_found() -> str:
#         """Response jika hadis tidak ditemukan"""
#         return (
#             "Maaf, hadis yang sesuai dengan pertanyaan Anda tidak ditemukan dalam basis data.\n\n"
#             "**Saran:**\n"
#             "- Coba kata kunci lain\n"
#             "- Upload dokumen hadis yang relevan\n"
#         )
    
#     @staticmethod
#     def format_only_dhaif_found(hadis_list: List[HadisValidated]) -> str:
#         """Response khusus jika hanya hadis dhaif yang ditemukan"""
#         response = "⚠️ **Hanya hadis dhaif yang ditemukan:**\n\n"
        
#         for hadis in hadis_list[:2]:
#             response += StrictResponseFormatter.format_single_hadis(hadis)
#             response += "\n"
        
#         response += (
#             "\n**Catatan penting:**\n"
#             "Hadis dhaif tidak dijadikan dalil utama dalam Islam. "
#             "Silakan konsultasikan dengan ulama untuk penjelasan lebih lanjut.\n"
#         )
        
#         return response


# class StrictPromptSystem:
#     """
#     🔐 SYSTEM PROMPT TERKUNCI
#     LLM tidak boleh keluar dari aturan ini
#     """
    
#     SYSTEM_PROMPT = """
# Kamu adalah chatbot hadis berbasis database.

# 🚫 DILARANG KERAS:
# - Mengarang hadis
# - Mengubah terjemah hadis
# - Menambah informasi di luar database
# - Menarik kesimpulan hukum sendiri
# - Membandingkan kitab tanpa diminta

# ✅ WAJIB:
# - Mengambil hadis HANYA dari database
# - Menyebutkan sumber dan derajat
# - Memberi makna singkat maksimal 2 kalimat
# - Gunakan bahasa netral dan edukatif

# Jika data tidak tersedia, katakan:
# "Hadis tidak ditemukan dalam basis data."

# Format jawaban sudah ditentukan sistem, jangan ubah!
# """
    
#     @staticmethod
#     def build_strict_prompt(query: str, validated_hadis: List[HadisValidated]) -> str:
#         """
#         Build prompt dengan constraint ketat
        
#         LLM hanya boleh:
#         1. Memilih hadis paling relevan
#         2. Membuat makna singkat (max 2 kalimat)
#         3. TIDAK BOLEH menambah info lain
#         """
        
#         if not validated_hadis:
#             return StrictPromptSystem.SYSTEM_PROMPT + "\n\nQuery: " + query + "\n\nJawab: Data tidak tersedia."
        
#         # Build context dari validated hadis
#         context = "Database Hadis (sudah tervalidasi):\n\n"
        
#         for i, hadis in enumerate(validated_hadis[:3], 1):
#             context += f"Hadis {i}:\n"
#             context += f"Terjemah: {hadis.terjemah[:200]}...\n"
#             context += f"Sumber: {hadis.sumber}\n"
#             context += f"Derajat: {hadis.derajat.value}\n\n"
        
#         prompt = f"""
# {StrictPromptSystem.SYSTEM_PROMPT}

# {context}

# Pertanyaan user: {query}

# Tugas kamu:
# 1. Pilih hadis paling relevan (berdasarkan sumber terpercaya)
# 2. Buat makna singkat (maksimal 2 kalimat, netral)
# 3. JANGAN tambah informasi lain

# Jawab HANYA dengan makna singkat:
# """
        
#         return prompt


# # =====================================================
# # INTEGRATION KE SISTEM EXISTING
# # =====================================================

# class StrictHadisService:
#     """
#     Service utama yang menggabungkan semua layer
    
#     Flow:
#     1. Vector search (existing)
#     2. Validation layer (new)
#     3. Format response (new)
#     4. Limited LLM call (new)
#     """
    
#     def __init__(self, llm_service):
#         self.llm = llm_service
#         self.validator = HadisValidator()
#         self.formatter = StrictResponseFormatter()
    
#     async def process_query(self, query: str, chunks: List[Dict]) -> Dict:
#         """
#         Process query dengan validation ketat
        
#         Returns:
#             {
#                 'answer': str,
#                 'validated_hadis': List[HadisValidated],
#                 'is_safe': bool
#             }
#         """
        
#         # Step 1: Validate semua chunks
#         validated_hadis = []
        
#         for chunk in chunks:
#             hadis = self.validator.validate_hadis(chunk)
#             if hadis:
#                 validated_hadis.append(hadis)
        
#         # Step 2: Check hasil validasi
#         if not validated_hadis:
#             return {
#                 'answer': self.formatter.format_not_found(),
#                 'validated_hadis': [],
#                 'is_safe': True
#             }
        
#         # Step 3: Check apakah hanya dhaif
#         only_dhaif = all(h.derajat == DerajatHadis.DHAIF for h in validated_hadis)
        
#         if only_dhaif:
#             return {
#                 'answer': self.formatter.format_only_dhaif_found(validated_hadis),
#                 'validated_hadis': validated_hadis,
#                 'is_safe': True
#             }
        
#         # Step 4: Prioritaskan shahih/hasan
#         prioritized = sorted(
#             validated_hadis,
#             key=lambda h: 0 if h.derajat == DerajatHadis.SHAHIH else 1
#         )
        
#         # Step 5: Generate makna singkat (LIMITED LLM)
#         best_hadis = prioritized[0]
        
#         if not best_hadis.makna_singkat:
#             makna = await self._generate_limited_makna(query, best_hadis)
#             best_hadis.makna_singkat = makna
        
#         # Step 6: Format final response
#         answer = self.formatter.format_single_hadis(best_hadis, include_makna=True)
        
#         # Tambahkan hadis lain jika ada
#         if len(prioritized) > 1:
#             answer += "\n\n**Hadis terkait lainnya:**\n\n"
#             for hadis in prioritized[1:3]:
#                 answer += f"- {hadis.sumber} (No. {hadis.nomor_hadis or 'N/A'})\n"
        
#         return {
#             'answer': answer,
#             'validated_hadis': prioritized,
#             'is_safe': True
#         }
    
#     async def _generate_limited_makna(self, query: str, hadis: HadisValidated) -> str:
#         """
#         Generate makna singkat dengan LLM terbatas
        
#         LLM HANYA boleh:
#         - Buat 1-2 kalimat penjelasan
#         - Netral, tidak judgmental
#         - Tidak boleh tambah info lain
#         """
        
#         limited_prompt = f"""
# Hadis:
# {hadis.terjemah}

# Sumber: {hadis.sumber}

# Tugas: Buat makna singkat (maksimal 2 kalimat) yang menjelaskan inti hadis ini.
# Gunakan bahasa netral dan edukatif.

# Makna singkat:
# """
        
#         try:
#             # Call LLM dengan constraint ketat
#             import ollama
#             response = ollama.generate(
#                 model="mistral",
#                 prompt=limited_prompt,
#                 options={
#                     "temperature": 0.1,
#                     "num_predict": 50,  # ❗ Max 50 tokens (2 kalimat)
#                     "stop": ["\n\n", "Hadis", "Sumber"]
#                 }
#             )
            
#             return response['response'].strip()
        
#         except Exception as e:
#             # Fallback: return generic
#             return "Hadis ini menjelaskan pentingnya nilai-nilai dalam Islam."
