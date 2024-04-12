from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()
import os
from gnews import GNews
google_news = GNews()
import nltk
from newspaper import Article
nltk.download('punkt')

# Mongodb
uri = os.environ.get("MONGODB_URI")
db = MongoClient(uri, ssl=True, tlsAllowInvalidCertificates=True)['mjd_2024']
print(db.list_collection_names())
collection = db.monitoramento_ppd

# OpenAi
openai_api_key = os.getenv("openai_api_key")
openai_api_key = os.environ["openai_api_key"]
from openai import OpenAI
client = OpenAI(api_key=openai_api_key)

# Credenciais do envio de email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from lxml.html import document_fromstring

#CÓDIGO

#Pegando notícias e adicionando resumo

def pega_noticia(tema):
  
    google_news.country = 'Brasil'
    google_news.language = 'portuguese brasil'
    google_news.period = '7d'
    google_news.max_results = 2

    lista_noticias = google_news.get_news(tema)
    coluna4 = collection.find({"url": {"$exists":True}})
    noticias_raspadas = []

    for noticia in lista_noticias:
        if not collection.find_one({"url": noticia["url"]}):
            noticias_raspadas.append(noticia)

    if noticias_raspadas:
        collection.insert_many(noticias_raspadas)    
        print(f"{len(noticias_raspadas)} notícias raspadas")  

    else:
        print("Nenhuma notícia foi encontrada")

def adiciona_resumo():
    for noticia in collection.find({"raspado": {"$exists": False}}):
            try:
                article = Article(noticia['url'])
                article.download()
                article.parse()
                article.nlp()
                novo_resumo = article.summary
                collection.update_one({"_id": noticia["_id"]},
                                    {"$set":
                                    {"description": novo_resumo,
                                    "raspado": True}})
            except Exception as e:
                print(f"Erro ao processar a notícia: {e}")
                continue  # Pula para a próxima notícia em caso de erro

    print("Os resumos foram adicionados.")

#Filtrando notícias que aconteceram no brasil e se houve violação com ChatGPT

def identifica_casos_brasileiros():
    noticias = collection.find({"caso brasileiro": {"$exists": False}})  # Encontra as notícias não avaliadas

    for noticia in noticias:
        titulo = noticia["title"]
        resumo = noticia["description"]

        pergunta1 = "Chat, vou te passar um resumo de uma notícia e quero que você responda apenas com 'true' ou 'false'\n\nRESUMO DA NOTÍCIA:\n\n"
        pergunta2 = "\n\nPERGUNTA:\n\nO caso se refere a algo que aconteceu no Brasil? Preste atenção. Pode ser que a notícia esteja falando de um caso que não aconteceu no território brasileiro."

        pergunta_completa = pergunta1 + titulo + "\n\n" + resumo + pergunta2

        chat = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": pergunta_completa,
                }
            ],
            model="gpt-3.5-turbo",
        )

        resposta = chat.choices[0].message.content

        # Converte a resposta para booleano
        if resposta.lower() == "true":
            resposta_booleana = True
        elif resposta.lower() == "false":
            resposta_booleana = False
        else:
            print("Resposta inválida. Utilizando False por padrão.")
            resposta_booleana = False

        # Atualiza a coleção MongoDB com a resposta do modelo
        collection.update_one({"_id": noticia["_id"]}, {"$set": {"caso brasileiro": resposta_booleana}})
        
        # Mostra como ficou o documento após o update
        updated_noticia = collection.find_one({"_id": noticia["_id"]})
        print(updated_noticia)

    print("Identificação de casos que aconteceram no Brasil concluída.")

def identifica_violacao():
    noticias = collection.find({"caso brasileiro": True, "relação com atuação profissional": {"$exists": False}})  # Encontra as notícias não avaliadas com caso brasileiro True

    for noticia in noticias:
        titulo = noticia["title"]
        resumo = noticia["description"]

        pergunta1 = "Chat, vou te passar um resumo de uma notícia e quero que você responda apenas com 'true' ou 'false'\n\nRESUMO DA NOTÍCIA:\n\n"
        pergunta2 = "\n\nPERGUNTA:\n\nO caso se refere a algo que aconteceu no Brasil? Preste atenção. Pode ser que a notícia esteja falando de um caso que não aconteceu no território brasileiro."

        pergunta_completa = pergunta1 + titulo + "\n\n" + resumo + pergunta2

        chat = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": pergunta_completa,
                }
            ],
            model="gpt-3.5-turbo",
        )

        resposta = chat.choices[0].message.content

        # Converte a resposta para booleano
        if resposta.lower() == "true":
            resposta_booleana = True
        elif resposta.lower() == "false":
            resposta_booleana = False
        else:
            print("Resposta inválida. Utilizando False por padrão.")
            resposta_booleana = False

        # Atualiza a coleção MongoDB com a resposta do modelo
        collection.update_one({"_id": noticia["_id"]}, {"$set": {"relação com atuação profissional": resposta_booleana}})
        
        # Mostra como ficou o documento após o update
        updated_noticia = collection.find_one({"_id": noticia["_id"]})
        print(updated_noticia)

    print("Identificação de casos que aconteceram no Brasil concluída.")

#Classifica a notícia

def classifica_violacao():

    todas_noticias = collection.find({
        "caso brasileiro": True,
        "relação com atuação profissional": True,
        "categoria e justificativa": {"$exists": False}
    })

    pergunta = """ Chat, eu vou te passar o resumo de uma notícia e quero que você faça duas coisas: classifique se a notícia e escreva uma justificativa em uma frase da sua escolha.

    Categorias:

    Ameaça física
    Ameaça digital
    Ameaça legal/Jurídica
    Outros

    Atenção: você deve me responder somente com o nome da classificação e a sua breve justificativa, nada além disso.

    Atenção: você deve usar a opção 'Ameaças legais/Jurídicas' apenas em casos em que profissionais da comunicação foram PROCESSADOS, PRESOS ou tiveram os seus equipamentos APREENDIDOS; Já a categoria 'Outros' você deve classificar em casos que não mencionam as categorias anteriores.

    Resumo da notícia:

    """

    for noticia in todas_noticias:
        titulo = noticia["title"]
        resumo = noticia["description"]

        pergunta_completa = pergunta + titulo + """

             """ + resumo

        chat = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": pergunta_completa,
                }
            ],
            model="gpt-3.5-turbo",
        )

        resposta = chat.choices[0].message.content

        collection.update_one({"_id": noticia["_id"]}, {"$set": {"categoria e justificativa": resposta}})
        print("Atualização na notícia com _id:", noticia["_id"], "com resposta:", resposta)

    print("Notícias devidamente classificadas")
  
#Cria conteúdo do e-mail e envia 

def conteudo_email():
    todas_noticias = collection.find({
        "categoria e justificativa": {"$exists": True},
        "e-mail enviado": {"$not": {"$regex": "Enviado"}}
    })

    resposta = []

    for noticia in todas_noticias:
        titulo = noticia["title"]
        descricao = noticia["description"]
        data = noticia["published date"]
        url = noticia["url"]
        categoria = noticia["categoria e justificativa"]

        resposta.append([titulo, descricao, data, url, categoria])

        # Atualiza o campo "e-mail enviado" para indicar que o e-mail foi enviado
        collection.update_one({"_id": noticia["_id"]}, {"$set": {"e-mail enviado": "Enviado"}})

    print("As atualizações foram enviadas por e-mail")
    return resposta

def envia_email():
    smtp_server = "smtp-relay.brevo.com"
    port = 587
    email = os.getenv("email")
    email = os.environ["email"]
    password = os.getenv("password")
    password = os.environ["password"]  

    remetente = os.getenv("remetente")
    remetente = os.environ["remetente"]  
    destinatarios = os.getenv("destinatarios")
    destinatarios = os.environ["destinatarios"]  
    titulo_email = "Atualização semanal: Monitoramento PPD"

    # Chama a função envia_email() e armazena o resultado
    resposta = conteudo_email()

    # Inicia a construção do corpo do e-mail em HTML
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monitoramento PPD</title>
    </head>
    <body>
        <h1>Atualizações do Monitoramento de PPD</h1>
        <p>
        As matérias encontradas foram:
        <ul>
    """

    # Adiciona cada notícia à mensagem HTML
    for noticia in resposta:
        titulo, descricao, url, veiculo, categoria = noticia
        html += f'<li><strong>Título:</strong> {titulo}<br>'
        html += f'<strong>Descrição:</strong> {descricao}<br>'
        html += f'<strong>URL:</strong> <a href="{url}">{url}</a><br>'
        html += f'<strong>Categoria:</strong> {categoria}</li><br>'

    # Finaliza o corpo HTML do e-mail
    html += """
        </ul>
        </p>
    </body>
    </html>
    """

    # Inicia conexão com o servidor SMTP
    server = smtplib.SMTP(smtp_server, port)
    server.starttls()
    server.login(email, password)

    # Prepara a mensagem do e-mail
    mensagem = MIMEMultipart()
    mensagem["From"] = remetente
    mensagem["To"] = ",".join(destinatarios)
    mensagem["Subject"] = titulo_email
    conteudo_html = MIMEText(html, "html")
    mensagem.attach(conteudo_html)

    # Envia o email
    return server.sendmail(remetente, destinatarios, mensagem.as_string())
