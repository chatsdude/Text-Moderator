import requests
from bs4 import BeautifulSoup

html=requests.get('')
raw = BeautifulSoup(html.text,'lxml')
for text in raw:
    print(text.encode('utf-8'))
