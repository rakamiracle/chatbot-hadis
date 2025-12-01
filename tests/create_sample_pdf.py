from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_sample_hadis_pdf():
    """Create sample PDF for testing"""
    pdf_path = "tests/fixtures/sample_hadis.pdf"
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    
    # Page 1
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, "Kumpulan Hadis Shahih")
    c.drawString(100, 700, "Hadis 1: Dari Abu Hurairah, Rasulullah SAW bersabda:")
    c.drawString(100, 680, "Barangsiapa beriman kepada Allah dan hari akhir,")
    c.drawString(100, 660, "hendaklah ia berkata baik atau diam.")
    c.drawString(100, 640, "(HR. Bukhari)")
    
    c.drawString(100, 600, "Hadis 2: Dari Aisyah RA, Rasulullah SAW bersabda:")
    c.drawString(100, 580, "Kebersihan adalah sebagian dari iman.")
    c.drawString(100, 560, "(HR. Muslim)")
    
    c.showPage()
    c.save()
    
    print(f"✓ Sample PDF created: {pdf_path}")

if __name__ == "__main__":
    import os
    os.makedirs("tests/fixtures", exist_ok=True)
    create_sample_hadis_pdf()
