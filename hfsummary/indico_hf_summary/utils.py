import requests
import markdown
import html2text


# html to markdown to feed LLM
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
    html = markdown.markdown(summary_text)
    return html
