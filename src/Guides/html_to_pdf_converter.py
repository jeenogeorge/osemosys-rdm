"""
Advanced HTML to PDF Converter with custom styling for each guide
Author: AFR_RDM Team
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import re

# Custom CSS for Guide PRIM Module Configuration - Responsive tables
CUSTOM_CSS_PRIM = """
<style>
    /* Hide sidebar navigation */
    .sidebar {
        display: none !important;
    }

    /* Adjust main content to use full width */
    .container {
        display: block !important;
    }

    .content {
        margin: 0 !important;
        max-width: 100% !important;
    }

    /* Make tables responsive */
    .table-wrapper {
        overflow-x: visible !important;
        width: 100%;
    }

    table {
        width: 100% !important;
        min-width: auto !important;
        table-layout: fixed !important;
        font-size: 8px !important;
    }

    th, td {
        padding: 4px 2px !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        font-size: 7px !important;
        line-height: 1.2 !important;
    }

    th {
        font-size: 7.5px !important;
        font-weight: 600 !important;
    }

    /* Specific column widths for better readability */
    th:nth-child(1), td:nth-child(1) {
        width: 18% !important;
    }

    th:nth-child(2), td:nth-child(2) {
        width: 30% !important;
    }

    th:nth-child(3), td:nth-child(3) {
        width: 15% !important;
    }

    th:nth-child(4), td:nth-child(4) {
        width: 20% !important;
    }

    th:nth-child(5), td:nth-child(5) {
        width: 17% !important;
    }

    /* Header adjustments */
    header {
        position: relative !important;
        padding: 1rem !important;
    }

    .header-text h1 {
        font-size: 1.5rem !important;
    }

    .header-text p {
        font-size: 0.9rem !important;
    }

    /* Content adjustments */
    .content h2 {
        font-size: 1.3rem !important;
        margin-top: 1.5rem !important;
    }

    .content h3 {
        font-size: 1.1rem !important;
        margin-top: 1rem !important;
    }

    .content h4 {
        font-size: 1rem !important;
    }

    .content p, .content li {
        font-size: 9px !important;
        line-height: 1.4 !important;
    }

    /* Code blocks */
    code {
        font-size: 7px !important;
    }

    pre {
        font-size: 8px !important;
        padding: 0.5rem !important;
    }

    /* Notes and boxes */
    .note, .important-box {
        font-size: 8px !important;
        padding: 0.5rem !important;
        margin: 0.5rem 0 !important;
    }

    /* Better spacing */
    body {
        margin: 0;
        padding: 0;
    }

    /* Print optimization */
    @media print {
        .sidebar {
            display: none !important;
        }

        table {
            page-break-inside: avoid !important;
        }

        tr {
            page-break-inside: avoid !important;
        }
    }
</style>
"""

def inject_custom_css(html_content, css_style):
    """Inject custom CSS into HTML content"""
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', f'{css_style}</head>')
    else:
        html_content = html_content.replace('<head>', f'<head>{css_style}')
    return html_content

def create_header_only_html(original_html):
    """Create HTML with only the header for first page (ARF_RDM guide)"""
    with open(original_html, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract just the header section
    header_match = re.search(r'(<header>.*?</header>)', content, re.DOTALL)
    if not header_match:
        raise ValueError("No header found in HTML")

    header_html = header_match.group(1)

    # Create a simple HTML with just the header, centered on page
    header_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RDM Model - User Guide</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        header {{
            background: linear-gradient(135deg, #1A2B4A 0%, #4A90E2 100%);
            color: white;
            padding: 4rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            width: 100%;
            text-align: center;
            position: static !important;
        }}
        .header-content {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .header-text h1 {{
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }}
        .header-text p {{
            opacity: 0.9;
            font-size: 1.2rem;
        }}
    </style>
</head>
<body>
    {header_html}
</body>
</html>"""

    return header_page

def create_content_without_header_sidebar(original_html):
    """Create HTML without header, sidebar, and progress bar (ARF_RDM guide)"""
    with open(original_html, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove progress bar
    content = re.sub(r'<div class="progress-bar">.*?</div>\s*', '', content, flags=re.DOTALL)

    # Remove header
    content = re.sub(r'<header>.*?</header>\s*', '', content, flags=re.DOTALL)

    # Remove sidebar
    content = re.sub(r'<nav class="sidebar"[^>]*>.*?</nav>\s*', '', content, flags=re.DOTALL)

    # Adjust container margin (no header at top)
    content = content.replace('margin: 120px auto 0;', 'margin: 0 auto;')

    # Hide sidebar and adjust content width in CSS
    additional_css = """
    <style>
        .sidebar {
            display: none !important;
        }
        .content {
            margin-left: 0 !important;
            max-width: 100% !important;
        }
        .container {
            display: block !important;
        }
        body {
            padding-top: 0 !important;
        }
    </style>
    """
    content = content.replace('</head>', f'{additional_css}</head>')

    return content

def convert_to_pdf(html_content, output_pdf, include_page_numbers=True):
    """Convert HTML content to PDF"""
    # Create temporary HTML file
    temp_html = Path("temp_conversion.html")
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html_content)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Load HTML
        page.goto(f"file:///{temp_html.resolve().as_posix()}")
        page.wait_for_load_state('networkidle')

        # Generate PDF
        page.pdf(
            path=str(output_pdf),
            format='A4',
            print_background=True,
            margin={
                'top': '15mm',
                'right': '10mm',
                'bottom': '15mm',
                'left': '10mm'
            },
            prefer_css_page_size=False,
            display_header_footer=include_page_numbers,
            header_template='<div></div>',
            footer_template='''
                <div style="font-size: 8px; text-align: center; width: 100%; margin: 0 10mm;">
                    <span class="pageNumber"></span> / <span class="totalPages"></span>
                </div>
            ''' if include_page_numbers else '<div></div>'
        )

        browser.close()

    # Clean up
    temp_html.unlink()

def add_page_numbers_to_pdf(input_pdf, output_pdf, start_page_num, total_pages):
    """Add custom page numbers to PDF"""
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    import io

    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()

    for page_num, page in enumerate(reader.pages, start=start_page_num):
        # Create a new PDF with the page number
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=A4)

        # Add page number at bottom center
        page_text = f"{page_num} / {total_pages}"
        can.setFont("Helvetica", 8)
        can.drawCentredString(A4[0] / 2, 20, page_text)
        can.save()

        # Move to the beginning of the BytesIO buffer
        packet.seek(0)

        # Read the page number PDF
        overlay_pdf = PdfReader(packet)

        # Merge the page number with the original page
        page.merge_page(overlay_pdf.pages[0])
        writer.add_page(page)

    # Write the output
    with open(output_pdf, 'wb') as output_file:
        writer.write(output_file)

def convert_arf_rdm_two_step(html_file, pdf_file):
    """Convert ARF_RDM guide using two-step method: header first, then content"""
    try:
        print(f"\nConverting {html_file.name} to PDF (two-step method)...")

        header_pdf = html_file.parent / "temp_header.pdf"
        content_pdf = html_file.parent / "temp_content.pdf"
        content_with_numbers_pdf = html_file.parent / "temp_content_numbered.pdf"

        # Step 1: Create header-only PDF
        print("  Step 1: Creating header page...")
        header_html = create_header_only_html(html_file)
        convert_to_pdf(header_html, header_pdf, include_page_numbers=False)
        print("    ✓ Header page created")

        # Step 2: Create content PDF without header/sidebar (no page numbers yet)
        print("  Step 2: Creating content pages...")
        content_html = create_content_without_header_sidebar(html_file)
        convert_to_pdf(content_html, content_pdf, include_page_numbers=False)
        print("    ✓ Content pages created")

        # Step 3: Calculate total pages and add page numbers
        print("  Step 3: Adding page numbers...")
        from PyPDF2 import PdfReader

        header_reader = PdfReader(str(header_pdf))
        content_reader = PdfReader(str(content_pdf))

        total_pages = len(header_reader.pages) + len(content_reader.pages)

        # Add page numbers to content (starting from 1, total includes header)
        add_page_numbers_to_pdf(content_pdf, content_with_numbers_pdf, 1, total_pages)
        print(f"    ✓ Page numbers added (1-{total_pages - 1} of {total_pages})")

        # Step 4: Merge PDFs
        print("  Step 4: Merging PDFs...")
        from PyPDF2 import PdfWriter

        # Read PDFs again with page numbers
        header_reader = PdfReader(str(header_pdf))
        content_reader = PdfReader(str(content_with_numbers_pdf))

        # Create writer and add all pages
        writer = PdfWriter()

        # Add header page (no page number)
        writer.add_page(header_reader.pages[0])

        # Add content pages (now with correct page numbers)
        for page in content_reader.pages:
            writer.add_page(page)

        # Write final PDF
        with open(pdf_file, 'wb') as output_file:
            writer.write(output_file)

        # Clean up temporary files
        header_pdf.unlink()
        content_pdf.unlink()
        content_with_numbers_pdf.unlink()

        print(f"  ✓ Successfully created {pdf_file.name}")
        print(f"    - Total pages: {total_pages}")
        print(f"    - Page 1: Header only (no page number visible)")
        print(f"    - Pages 2-{total_pages}: Content with page numbers (1/{total_pages} to {total_pages-1}/{total_pages})")
        return True

    except Exception as e:
        print(f"  ✗ Error converting {html_file.name}: {e}")
        import traceback
        traceback.print_exc()
        # Clean up temporary files if they exist
        if 'header_pdf' in locals() and header_pdf.exists():
            header_pdf.unlink()
        if 'content_pdf' in locals() and content_pdf.exists():
            content_pdf.unlink()
        if 'content_with_numbers_pdf' in locals() and content_with_numbers_pdf.exists():
            content_with_numbers_pdf.unlink()
        return False

def convert_prim_simple(html_file, pdf_file, custom_css):
    """Convert PRIM guide using simple method with CSS injection"""
    try:
        print(f"\nConverting {html_file.name} to PDF...")

        # Read the HTML file
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Inject custom CSS
        html_content = inject_custom_css(html_content, custom_css)
        print("  ✓ Custom CSS injected")

        # Create a temporary HTML file with modifications
        temp_html_file = html_file.parent / f"temp_{html_file.name}"
        with open(temp_html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Convert to PDF
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # Load the modified HTML file
            page.goto(f"file:///{temp_html_file.resolve().as_posix()}")
            page.wait_for_load_state('networkidle')

            # Generate PDF with optimized settings
            page.pdf(
                path=str(pdf_file),
                format='A4',
                print_background=True,
                margin={
                    'top': '15mm',
                    'right': '10mm',
                    'bottom': '15mm',
                    'left': '10mm'
                },
                prefer_css_page_size=False,
                display_header_footer=True,
                header_template='<div></div>',
                footer_template='''
                    <div style="font-size: 8px; text-align: center; width: 100%; margin: 0 10mm;">
                        <span class="pageNumber"></span> / <span class="totalPages"></span>
                    </div>
                '''
            )

            browser.close()

        # Clean up temporary file
        temp_html_file.unlink()

        print(f"  ✓ Successfully created {pdf_file.name}")
        return True

    except Exception as e:
        print(f"  ✗ Error converting {html_file.name}: {e}")
        # Clean up temporary file if it exists
        if 'temp_html_file' in locals() and temp_html_file.exists():
            temp_html_file.unlink()
        return False

def main():
    # Define the guides directory
    guides_dir = Path(".")

    # Configuration for each guide
    guides_config = [
        {
            'html_file': 'Guide ARF_RDM.html',
            'method': 'two_step',
            'description': 'AFR_RDM Guide (header on first page only, no sidebar)'
        },
        {
            'html_file': 'Guide PRIM Module Configuration.html',
            'method': 'simple',
            'custom_css': CUSTOM_CSS_PRIM,
            'description': 'PRIM Configuration Guide (responsive tables, no sidebar)'
        }
    ]

    print("=" * 70)
    print("Advanced HTML to PDF Conversion Tool")
    print("=" * 70)

    success_count = 0
    total_count = len(guides_config)

    for config in guides_config:
        html_file = config['html_file']
        html_path = guides_dir / html_file
        pdf_file = html_file.replace('.html', '.pdf')
        pdf_path = guides_dir / pdf_file

        print(f"\n[{guides_config.index(config) + 1}/{total_count}] {config['description']}")

        if not html_path.exists():
            print(f"  ✗ Warning: {html_path} not found. Skipping...")
            continue

        # Use appropriate conversion method
        if config['method'] == 'two_step':
            if convert_arf_rdm_two_step(html_path, pdf_path):
                success_count += 1
        elif config['method'] == 'simple':
            if convert_prim_simple(html_path, pdf_path, config['custom_css']):
                success_count += 1

    print("\n" + "=" * 70)
    print(f"Conversion complete: {success_count}/{total_count} files converted successfully")
    print("=" * 70)

    if success_count == total_count:
        print("\n✓ All guides converted successfully!")
    else:
        print(f"\n⚠ {total_count - success_count} file(s) failed to convert.")

if __name__ == "__main__":
    main()
