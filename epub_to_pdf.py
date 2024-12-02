import requests
import streamlit as st
from ebooklib import epub
import ebooklib
from bs4 import BeautifulSoup
import io
import tempfile
import os
import subprocess
import json
import re
import base64
import pdfkit
import csv
from datetime import datetime
from user_agents import parse
from weasyprint import HTML, CSS
# Global constant for debugging
DEBUG = False

# Load fonts from JSON file
with open('fonts.json') as f:
    fonts = json.load(f)

def sanitize_filename(filename):
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)

def convert_image_to_base64(image_content):
    return base64.b64encode(image_content).decode('utf-8')

def add_cover_page(html_buffer, title, author):
    html_buffer.write('''
    <div style="display: flex; justify-content: center; align-items: center; height: 100vh; text-align: center;">
        <div>
            <h1 style="font-size: 3em;">{}</h1>
            <h2 style="font-size: 2em; color: gray;">{}</h2>
        </div>
    </div>
    '''.format(title, author))

def epub_to_html(epub_file_path, text_font, text_size, header_font):
    # Load the EPUB file from the temporary file
    book = epub.read_epub(epub_file_path)

    # Get book title and author
    title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else 'Untitled'
    author = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else 'Unknown Author'

    # Create an HTML buffer
    html_buffer = io.StringIO()
    html_buffer.write(f'''
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @font-face {{
                font-family: '{text_font}';
                src: url('{fonts[text_font]}') format('woff2');
            }}
            @font-face {{
                font-family: '{header_font}';
                src: url('{fonts[header_font]}') format('woff2');
            }}
            body {{ font-family: '{text_font}'; font-size: {text_size}em; }}
            h1, h2, h3, h4, h5, h6 {{ font-family: '{header_font}'; }}
        </style>
    </head>
    <body>
    ''')

    # Add cover page
    add_cover_page(html_buffer, title, author)

    # Add cover image if available
    cover_item = book.get_item_with_id('cover')
    if cover_item:
        cover_image = cover_item.get_content()
        cover_image_base64 = convert_image_to_base64(cover_image)
        html_buffer.write(f'<img src="data:image/jpeg;base64,{cover_image_base64}" style="width:100%;height:auto;"/>')

    # Iterate through the EPUB items
    items = book.get_items()
    for i, item in enumerate(items):
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            if i >0:
                html_buffer.write('<div style="page-break-before: always;"></div>')
            # Parse the HTML content
            soup = BeautifulSoup(item.get_body_content(), 'html.parser')
            html_buffer.write(str(soup))
            # Add page break after each chapter except the last one


    html_buffer.write('</body></html>')
    html_buffer.seek(0)
    return html_buffer


def html_to_pdf(html_buffer, pdf_path):


    # Create a WeasyPrint HTML object from the buffer
    html = HTML(string=html_buffer.getvalue())

    # Optional: Add some basic CSS for better rendering
    css = CSS(string='''
    @page {
        size: A4;
        margin: 1cm;
    }
    body {
        font-family: Arial, sans-serif;
        line-height: 1.6;
    }
    ''')

    # Write the PDF to the specified path
    html.write_pdf(pdf_path, stylesheets=[css])

def html_to_pdf_wkhtml2pdf(html_buffer, pdf_path):
    # Save the HTML content to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as temp_html:
        temp_html.write(html_buffer.getvalue().encode('utf-8'))
        temp_html_path = temp_html.name

    # Convert the HTML file to PDF using pdfkit
    pdfkit.from_file(temp_html_path, pdf_path)

    # Delete the temporary HTML file
    os.remove(temp_html_path)
def log_user_activity(ip_address, browser, epub_file_name):
    log_file = 'user_activity_log.csv'
    fieldnames = ['datetime', 'ip_address', 'browser', 'epub_file_name']
    log_data = {
        'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ip_address': ip_address,
        'browser': browser,
        'epub_file_name': epub_file_name
    }

    file_exists = os.path.isfile(log_file)
    with open(log_file, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(log_data)



# Streamlit app
st.title('📚 EPUB to PDF Converter for Kids 📚')
st.markdown('Convert your favorite EPUB books to PDF for easy reading and printing! 🌟')

# File uploader
uploaded_file = st.file_uploader('Upload your EPUB file here:', type=['epub'])

# Font selection
with st.container():
    col1, col2=st.columns(2)
    text_font = col1.selectbox('Select Text Font', list(fonts.keys()))
    text_size = col2.slider('Select Text Size', 0.5, 2.0, 1.0, step=0.1)
with st.container():
    col1, col2=st.columns(2)
    header_font = col1.selectbox('Select Header Font', list(fonts.keys()))


# Convert button
with st.container():
    col1, col2, col3 = st.columns(3)
    convert_button = col1.button('Convert', key='convert_button', help='Convert EPUB to PDF', type='primary', disabled=uploaded_file is None)
    # Placeholders for download buttons
    pdf_download_placeholder = col2.empty()
    html_download_placeholder = col3.empty()

if uploaded_file is not None:
    st.success('File uploaded successfully! 🎉')

    # Sanitize file name
    original_filename = uploaded_file.name
    sanitized_filename = sanitize_filename(original_filename)
    print(f"Sanitized file name: {sanitized_filename}")

    # Log user activity
    query_params = st.session_state.get("query_params", {})
    ip_address = query_params.get('ip', [''])[0]
    user_agent = query_params.get('user-agent', [''])[0]
    browser = parse(user_agent).browser.family
    log_user_activity(ip_address, browser, original_filename)

    if convert_button:
        # Save the uploaded EPUB file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_epub:
            temp_epub.write(uploaded_file.read())
            temp_epub_path = temp_epub.name
        print(f"EPUB file saved to temporary file: {temp_epub_path}")

        # Convert EPUB to HTML with selected fonts and sizes
        html_buffer = epub_to_html(temp_epub_path, text_font, text_size, header_font)

        # Create a temporary PDF file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            pdf_path = temp_pdf.name

        # Convert HTML to PDF
        html_to_pdf(html_buffer, pdf_path)

        # Display download buttons in the same line as the Convert button

        pdf_download_placeholder.download_button(
            label='📥 Download PDF 📄: ',
            data=open(pdf_path, 'rb').read(),
            file_name=f'{sanitized_filename}.pdf',
            mime='application/pdf',
            key='download_pdf_button'
        )

        html_download_placeholder.download_button(
            label='📥 Download HTML 📄: ',
            data=html_buffer.getvalue().encode('utf-8'),
            file_name=f'{sanitized_filename}.html',
            mime='text/html',
            key='download_html_button'
        )

        # Save files for debugging if DEBUG is True
        if DEBUG:
            os.makedirs('data', exist_ok=True)
            with open(f'data/{sanitized_filename}.epub', 'wb') as f:
                f.write(open(temp_epub_path, 'rb').read())
            with open(f'data/{sanitized_filename}.html', 'w', encoding='utf-8') as f:
                f.write(html_buffer.getvalue())
            with open(f'data/{sanitized_filename}.pdf', 'wb') as f:
                f.write(open(pdf_path, 'rb').read())

        # Delete the temporary files
        os.remove(temp_epub_path)
        os.remove(pdf_path)
else:
    st.info('Please upload an EPUB file to start the conversion. 📖')

st.markdown('Enjoy reading your books on any device! 📱💻📚')
