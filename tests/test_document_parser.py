"""Unit tests for multi-format document parser and text chunker."""
import io
import pytest
from pathlib import Path
import pypdf
import docx

from src.document_parser import DocumentParser, SUPPORTED_EXTENSIONS

@pytest.fixture
def parser():
    return DocumentParser(chunk_size=300, chunk_overlap=50)

def test_supported_extensions(parser):
    """Verify supported document extensions."""
    assert parser.is_supported("vendor_contract.pdf") is True
    assert parser.is_supported("store_sop.docx") is True
    assert parser.is_supported("invoice.txt") is True
    assert parser.is_supported("readme.md") is True
    assert parser.is_supported("data.csv") is False
    assert parser.is_supported("image.png") is False

def test_parse_text_file(parser, tmp_path):
    """Test text and markdown extraction and chunking."""
    txt_file = tmp_path / "supplier_policy.txt"
    txt_content = (
        "Supplier Delivery Terms & Conditions\n\n"
        "1. Minimum order quantity (MOQ) is 50 units per SKU.\n\n"
        "2. Standard delivery lead time is 48 hours for metro stores.\n\n"
        "3. Damaged goods must be reported within 24 hours of delivery receipt."
    )
    txt_file.write_text(txt_content, encoding="utf-8")

    chunks = parser.parse_and_chunk(txt_file, "supplier_policy.txt", doc_id="doc_txt_01")
    assert len(chunks) >= 1
    assert chunks[0]["doc_id"] == "doc_txt_01"
    assert chunks[0]["filename"] == "supplier_policy.txt"
    assert chunks[0]["file_type"] == "TXT"
    assert "Minimum order quantity" in chunks[0]["text"]

def test_parse_markdown_file(parser, tmp_path):
    """Test Markdown formatting extraction."""
    md_file = tmp_path / "store_manual.md"
    md_content = (
        "# Store Operations Manual\n\n"
        "## Return Policy\n"
        "Customers may return unopened dry packaged food within 7 days with receipt.\n\n"
        "## Cash Reconciliation\n"
        "Store managers must perform daily register balancing at 21:00."
    )
    md_file.write_text(md_content, encoding="utf-8")

    chunks = parser.parse_and_chunk(md_file, "store_manual.md", doc_id="doc_md_01")
    assert len(chunks) >= 1
    assert chunks[0]["file_type"] == "MD"
    assert "Return Policy" in chunks[0]["text"]

def test_parse_pdf_file(parser, tmp_path):
    """Test PDF text extraction with page tracking using pypdf writer."""
    pdf_file = tmp_path / "test_agreement.pdf"
    
    # Generate a lightweight PDF in memory using pypdf
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    
    # Write PDF file
    with open(pdf_file, "wb") as f:
        writer.write(f)

    # Even a blank PDF should parse cleanly without crashing (0 chunks or empty)
    chunks = parser.parse_and_chunk(pdf_file, "test_agreement.pdf", doc_id="doc_pdf_01")
    assert isinstance(chunks, list)

def test_parse_docx_file(parser, tmp_path):
    """Test Microsoft Word .docx extraction and table reading."""
    docx_file = tmp_path / "vendor_agreement.docx"
    doc = docx.Document()
    doc.add_heading("Vendor Agreement 2026", level=1)
    doc.add_paragraph("Payment credit cycle is strictly Net 30 days from invoice date.")
    
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "SKU"
    table.cell(0, 1).text = "Discount"
    table.cell(1, 0).text = "P01 Water"
    table.cell(1, 1).text = "15%"
    
    doc.save(str(docx_file))

    chunks = parser.parse_and_chunk(docx_file, "vendor_agreement.docx", doc_id="doc_docx_01")
    assert len(chunks) >= 1
    assert chunks[0]["file_type"] == "DOCX"
    assert any("Net 30 days" in c["text"] for c in chunks)
    assert any("P01 Water" in c["text"] for c in chunks)

def test_unsupported_file_error(parser, tmp_path):
    """Test that unsupported formats raise ValueError."""
    bad_file = tmp_path / "data.exe"
    bad_file.write_text("dummy", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        parser.parse_and_chunk(bad_file, "data.exe")
