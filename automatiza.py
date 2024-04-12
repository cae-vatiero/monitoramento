from pymongo import MongoClient
from dotenv import load_dotenv
import os
from gnews import GNews
google_news = GNews()
import nltk
from newspaper import Article
nltk.download('punkt')

# Mongodb
load_dotenv()
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

import re
import smtplib
import unicodedata
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from lxml.html import document_fromstring

from robo import (pega_noticia, adiciona_resumo, identifica_casos_brasileiros,
                  identifica_violacao, classifica_violacao, envia_email)

temas = ["jornalista AND atacado", "imprensa AND atacada"]

for tema in temas:
    pega_noticia(tema)
    adiciona_resumo()
    identifica_casos_brasileiros()
    identifica_violacao()
    classifica_violacao()

envia_email()



