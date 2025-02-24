from docx import Document

def split_text_into_chunks(text, max_words):
    """
    Splits text into chunks, each chunk containing at most max_words words.
    Args:
    text (str): The input text to be split.
    max_words (int): Maximum number of words per chunk.
    Returns:
    List of strings: Each string is a chunk of text.
    """
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        chunks.append(chunk)
    
    return chunks

def read_docx_in_parts(file_path, max_words_per_chunk=200):
    """Reads a .docx file and splits it into parts where each part has a maximum of `max_words_per_chunk` words."""
    doc = Document(file_path)
    paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]  # Filter empty paragraphs
    
    # Combine all paragraphs into one big text
    full_text = "\n".join(paragraphs)
    
    # Split the full text into chunks, each containing up to `max_words_per_chunk` words
    parts = split_text_into_chunks(full_text, max_words_per_chunk)
    
    return parts
