import re
import requests
from lxml import etree, html as lxml_html
from lxml.html.clean import Cleaner


# cleaning html text from tags 
def clean_html_text(raw_html):
    try:
        # parse HTML and extract text content
        html_element = lxml_html.fromstring(raw_html)
        cleaner = Cleaner(remove_tags=['p', 'div', 'span', 'a', 'ul', 'ol', 'li'])
        cleaned_element = cleaner.clean_html(html_element)
        cleaned_str = etree.tostring(cleaned_element, method='text', encoding='unicode')
        
        # normalize whitespace
        cleaned_str = re.sub(r'\s+', ' ', cleaned_str).strip()
        
        return cleaned_str
    except Exception as e:
        return f"[error cleaning HTML: {e}]"


# chunking function
def chunk_text(text: str, max_tokens=1500):
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), max_tokens):
        chunk = ' '.join(words[i:i + max_tokens])
        chunks.append(chunk)
    
    return chunks

def build_prompt(text: str) -> str:
    return f"""Imagine you're a stand-up comedian summarizing a meeting. Be funny, witty, but keep the core ideas intact.
Every bullet should sound like you're roasting the meeting — without being cruel. Stay fact-based.
End with a mic drop line.

Format each section like this:
**Section Title**
• First bullet point
• Second bullet points

Now, summarize the following meeting minutes: {text} 
"""


# convert text to html in the end
def convert_text_to_html_sections(summary_text: str) -> str:
    html_sections = []
    current_section = None
    current_bullets = []
    
    for line in summary_text.splitlines():
        line = line.strip()
        if not line:
            continue
            
        # checking for **Section Title** - but what if it sections start with other symbols - rip
        if line.startswith("**") and line.endswith("**"):
            # save previous section if exists
            if current_section and current_bullets:
                html_sections.append(f"<b>{current_section}</b><ul>{''.join(current_bullets)}</ul>")
            
            # start new section
            current_section = line.strip("*").strip()
            current_bullets = []
            
        # cheking for bullet point: • bullet text - again if bullet points staart with another  symbol - rip
        elif line.startswith("•"):
            bullet_text = line[1:].strip()  # remove • and whitespace
            current_bullets.append(f"<li>{bullet_text}</li>")
    
    # add the last section
    if current_section and current_bullets:
        html_sections.append(f"<b>{current_section}</b><ul>{''.join(current_bullets)}</ul>")
    
    return "\n".join(html_sections)



# calling the hf-qwen25-32b model
def cern_qwen(message_text: str, token: str):
    url = "https://ml.cern.ch/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Host": "hf-qwen25-32b.genai.ml.cern.ch"
    }
    data = {
        "model": "hf-qwen25-32b",
        "messages": [
            {"role": "user", "content": message_text}
        ],
        "max_tokens": 1024,
        "stream": False
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.ok:
            return response.json()
        else:
            print("Error:", response.status_code, response.text)
            return None
    except Exception as e:
        print("Request failed:", e)
        return None


