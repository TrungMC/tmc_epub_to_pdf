import streamlit as st
import ebooklib
from ebooklib import epub
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from bs4 import BeautifulSoup
import io
import tempfile
import os

def epub_to_pdf(epub_file):
    try:
        # Debug print: Start of function
        print("Starting EPUB to PDF conversion...")

        # Save the uploaded EPUB file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_epub:
            temp_epub.write(epub_file.read())
            temp_epub_path = temp_epub.name
        print(f"EPUB file saved to temporary file: {temp_epub_path}")

        # Load the EPUB file from the temporary file
        book = epub.read_epub(temp_epub_path)
        print("EPUB file loaded successfully.")

        # Create a PDF canvas in memory
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        width, height = letter
        print("PDF canvas created.")

        # Iterate through the EPUB items
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Parse the HTML content
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                text = soup.get_text()

                # Write the text to the PDF
                c.drawString(30, height - 40, text)
                c.showPage()
                print(f"Processed item: {item.get_name()}")

        # Save the PDF
        c.save()
        pdf_buffer.seek(0)
        print("PDF saved successfully.")

        # Delete the temporary EPUB file
        os.remove(temp_epub_path)
        print(f"Temporary EPUB file deleted: {temp_epub_path}")

        return pdf_buffer

    except Exception as e:
        print(f"Error during conversion: {e}")
        return None

# Streamlit app
st.title('📚 EPUB to PDF Converter for Kids 📚')
st.markdown('Convert your favorite EPUB books to PDF for easy reading and printing! 🌟')

# File uploader
uploaded_file = st.file_uploader('Upload your EPUB file here:', type=['epub'])

if uploaded_file is not None:
    st.success('File uploaded successfully! 🎉')
    pdf_buffer = epub_to_pdf(uploaded_file)

    if pdf_buffer:
        # Provide download button for the PDF
        st.download_button(
            label='📥 Download PDF',
            data=pdf_buffer,
            file_name='converted_book.pdf',
            mime='application/pdf'
        )
        st.balloons()
    else:
        st.error('Failed to convert EPUB to PDF. Please check the console for more details.')
else:
    st.info('Please upload an EPUB file to start the conversion. 📖')

st.markdown('Enjoy reading your books on any device! 📱💻📚')
