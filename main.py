from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import requests
import re
from langchain_community.document_transformers import BeautifulSoupTransformer
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from yandex_cloud_ml_sdk import YCloudML
from urllib.parse import urlencode
import requests
from bs4 import BeautifulSoup

def extract_elements_with_classes(text):
   
    # Парсим HTML с помощью BeautifulSoup
    soup = BeautifulSoup(text, 'html.parser')
    
    # Определяем целевые классы
    target_classes = {'Link', 'Link_theme_outer', 'Path-Item', 'link', 'path__item'}
    
    # Ищем элементы, содержащие все указанные классы
    elements = soup.find_all(lambda tag: 
        tag.has_attr('class') and 
        target_classes.issubset(tag['class'])
    )
    
    # Извлекаем текст из найденных элементов
    results = [element.get('href') for element in elements[:3]]
    
    return results

load_dotenv()

YC_FOLDER_ID = os.getenv('YC_FOLDER_ID')
YC_API_KEY = os.getenv('YC_API_KEY')
YC_SEARCH_API_KEY = os.getenv('YC_SEARCH_API_KEY')
app = Flask(__name__)
# llm = OllamaLLM(
#     model="qwen2.5:14b",
#     temperature=0,
# )
# llm = YandexGPT()
sdk = YCloudML(
    folder_id=YC_FOLDER_ID,
    auth=YC_API_KEY,
)

model = sdk.models.completions("yandexgpt")
model = model.configure(temperature=0.2)

def search_web(query):
    # querystring = {"q":query,"lr":"ru-Ru","num":"2"}  
    querystring = {"query":query,"lr":"ru-Ru","num":"2","folderid":YC_FOLDER_ID,"apikey":YC_SEARCH_API_KEY}    
    try:
        response = requests.get('https://yandex.ru/search/xml/html', params=querystring)
        response.raise_for_status()
        return extract_elements_with_classes(response.text)
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
        "Answer the question based only on the context provided. Write text which refers to answer\n\n"+
        "Context:\n"
    )
    content_end = f"\n\nQuestion: {llm_query}\n"
    
    content = content_start + "\n\n---\n\n".join(search_results) + content_end
    return content

def create_completion_ollama(prompt):
    completion = model.run(prompt)
    return completion.alternatives[0].text

def remove_all_think_tags(text: str) -> str:
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

prompt = ChatPromptTemplate.from_template(
    """Answer the question based only on the context provided. And write some reasoning

Context: {context}

Question: {question}"""
)


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def find_first_digit(s: str) -> int:
    for c in s:
        if c.isdigit():
            return int(c)
    return 1

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
    res = model.run({'role': 'user', 'text': f"Напиши в ответе только соотвествующую цифру ответа(должен быть номер ответа, а не его значение). Если вопрос не подразумевает выбор из вариантов ответа, то верни null. Вопрос: \"{data['query']}\"Используй только данные из контекста. Контекст: {reasoning}"}).alternatives[0].text

    return jsonify({
        "id": data['id'],
        "answer": find_first_digit(res) if res !="null" else None,
        "reasoning": reasoning + "\n Ответ сгенерирован YandexGPT",
        "sources": urls
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)