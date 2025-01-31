from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import requests
import re
from langchain_community.document_transformers import BeautifulSoupTransformer
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

from langchain_core.documents import Document

load_dotenv()

SEARCH_API_KEY = os.getenv('SEARCH_API_KEY')

app = Flask(__name__)
llm = OllamaLLM(
    model="qwen2.5:14b",
    temperature=0,
)

url = "https://google-search72.p.rapidapi.com/search"

headers = {
	"x-rapidapi-key": SEARCH_API_KEY,
	"x-rapidapi-host": "google-search72.p.rapidapi.com"
}

def search_web(query):
    querystring = {"q":query,"lr":"ru-Ru","num":"2"}    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        results = response.json()
        return [result['link'] for result in results["items"]]
    except Exception as e:
        app.logger.error(f"Bing search error: {str(e)}")
        return []

def ddg_search(query):
    urls = search_web(query)
    docs = get_page(urls)    
    content = []
    for doc in docs:
        page_text = re.sub("\n\n+", "\n", doc.page_content)
        text = truncate(page_text)
        content.append(text)
    
    return content, urls

def get_page(urls):
    html =[Document( page_content=requests.get(url).text) for url in urls]
    bs_transformer = BeautifulSoupTransformer()
    docs_transformed = bs_transformer.transform_documents(
        html, 
        tags_to_extract=["p"], 
        remove_unwanted_tags=["a", "script", "style"]
    )
    
    return docs_transformed

def truncate(text):
    return " ".join(text.split()[:400])
# Answer the question using only the context below. You should write only the correct digit of answer
def create_prompt_ollama(llm_query, search_results):
    content_start = (
        "Answer the question based only on the context provided.\n\n"+
        "Context:\n"
    )
    content_end = f"\n\nQuestion: {llm_query}\n"
    
    content = content_start + "\n\n---\n\n".join(search_results) + content_end
    return [{'role':"user", 'content':content}]

def create_completion_ollama(prompt):
    completion = llm.invoke(prompt)
    return completion

def remove_all_think_tags(text: str) -> str:
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

prompt = ChatPromptTemplate.from_template(
    """Answer the question based only on the context provided.

Context: {context}

Question: {question}"""
)


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


@app.route('/api/request', methods=['POST'])
def handle_request():
    data = request.get_json()
    
    if not data or 'query' not in data or 'id' not in data:
        return jsonify({"error": "Invalid request format"}), 400
    
    search_query = create_completion_ollama(
            f"Выдели из текста запрос для поисковика без вариантов ответа. Напиши в ответе только вопрос: {data['query']}"
        )
    context, urls = ddg_search(search_query)
    prompt = create_prompt_ollama(data['query'], context)
    reasoning = create_completion_ollama(prompt)
    res = llm.invoke([{'role': 'user', 'content': f"Напиши в ответе только соотвествующую цифру ответа(должен быть номер ответа, а не его значение). Вопрос: \"{data['query']}\"Используй только данные из контекста. Контекст: {reasoning}"}])

    return jsonify({
        "id": data['id'],
        "answer": res,
        "reasoning": reasoning,
        "sources": urls
    })

if __name__ == '__main__':
    app.run(debug=True)