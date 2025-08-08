import re
import requests
from lxml import etree, html as lxml_html
from lxml.html.clean import Cleaner
import markdown
import html2text

# clean html tags from text in the first place
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

# html to markdown to feed llm
def html_to_markdown(html_string):
    h = html2text.HTML2Text() 
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0  
    return h.handle(html_string)



# chunking
def chunk_text(text: str, max_tokens=1500):
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), max_tokens):
        chunk = ' '.join(words[i:i + max_tokens])
        chunks.append(chunk)
    
    return chunks


# prompt 
def build_prompt(text: str) -> str:
    return f"""You are a precise assistant that summarizes meeting minutes accurately and clearly. Stick to the facts. Do not add opinions, assumptions, or inferred content.

    Instructions: 

    Use concise bullet points, grouped into clearly named sections.
    Avoid assumptions or repetition.
    Ensure the summary is easy to scan and logically structured.
    Do not explain your reasoning, process, or how you grouped the content. Only output the final summary.
    DO NOT create "Miscellaneous", "Misc", "Other", or "General" sections.
    Omit the miscellaneous meeting minutes and exclude them in the summary.
    Combine the relevant meeting minutes under the same section.
    Limit to maximum 2 bullet points for each section.

    Format each section like this:
    Section Title
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
            
        # checking for **Section Title** - but what if sections start with other symbols - rip
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







# call model hf-qwen25-32b
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

# convert markdown to html text when returning the summary
def markdown_to_html(summary_text: str) -> str:
    #summary_text = re.sub(r"(?m)^•\s*", "- ", summary_text)
    html = markdown.markdown(summary_text)
    return html
    