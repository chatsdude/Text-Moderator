from flask import Flask,render_template,request,Response
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import sys
import re
import spacy
import pickle
import json
from sklearn.metrics import classification_report
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import AdaBoostClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.ensemble import VotingClassifier
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

done,safe,hate,off=False,False,False,False
predicted_op,scraped_text,text="","",""
nlp=spacy.load('en_core_web_md')
#client=MongoClient('localhost',27017)
#db=client['hate_speech_data']
#hate_db= db.hate_db
app=Flask(__name__)

try:
    mongo=MongoClient(host="localhost",port=27017,serverSelectionTimeoutMS=1000)
    db=mongo.hate
    mongo.server_info()
except:
    print("Error-Cannot connect to db")

def test_db():
    if request.form['button']=='Yes':
        return Response(response=json.loads({name:"X",age:"y"}),status=200,mimetype="application/json")
    elif request.form['button']=="No":
        return Response(response=json.loads({name:"Not X",age:"Not y"}),status=200,mimetype="application/json")

def feedback_to_db(pop="Not correct"):
        global scraped_text,predicted_op,text
        try:
            schema={'URL': text,'Text obtained':scraped_text ,'Predicted_output':predicted_op,'User_thinks':pop}
            db_response=db.hatespeech.insert_one(schema)
            print(db_response.inserted_id)
        except Exception as ex:
            print(ex)
        return render_template('try.html',thank=f"Thank you for your feedback.")

def show_working_msg():
    return render_template('try.html',working=f"Working on it...please wait")

def show_need_more_time():
    return render_template('try.html',working=f"This might take a while!")


def cleaner(text):
    text=text.lower()
    cleaned=re.sub(r'[^a-zA-Z]',' ',text)
    sent=nlp(cleaned)
    tokens=[text for text in sent if (text.is_stop==False)]
    tokens=[text for text in tokens if (text.is_punct)==False]
    tokens=[text.lemma_ for text in tokens]
    to_string=" ".join(tokens)
    clean=re.sub(r'\s{2}|\s{3}|\s{4}|\s{5}',' ',to_string)
    clean=re.sub(r'\s\w\s',' ',clean)
    clean=re.sub(r'\s(ve)\s|\s(nd)\s|\s(st)\s|\s(th)\s|\s(rd)\s','',clean)
    return clean

def ml_model(sentence):
    tokens=cleaner(sentence)
    vectors=nlp(tokens).vector.reshape(1,-1)
    vc_model=pickle.load(open('Voting.pkl','rb'))
    op=vc_model.predict(vectors)
    prob=vc_model.predict_proba(vectors)
    return op,prob

def scraping_func_bs4(sent):
    html=requests.get(sent)
    raw = BeautifulSoup(html.text, 'html.parser').get_text()
    return raw

def scraping_func_selenium(sent):
    options=Options()
    options.headless=True
    options.add_argument("--window-size=1920,1200")
    DRIVER_PATH= "C:/Users/acer/chromedriver_win32/chromedriver"
    driver=webdriver.Chrome(options=options,executable_path=DRIVER_PATH)
    driver.get(sent)
    h1=driver.title
    if '|' in h1:
        h1=h1[:h1.find('|')]
    if h1=="" or len(h1)<=3:
        #Code for handling exception error.
        driver.quit()
        return render_template('test.html',error_message='Oops something went wrong.Please try again.')
    return h1

def check_db():
    global predicted_op
    if request.method=='POST':
        if request.form['button']=='Yes':
            feedback_to_db(predicted_op)
        if request.form['button']=='No':
            feedback_to_db()

@app.route("/")
@app.route("/index.html")
def home_template():
    #Home page.
    return render_template('index.html')

@app.route("/Mission")
def mission_template():
    #Mission page.
    pass

@app.route("/try.html",methods=['GET'])
def try_template():
    return render_template('try.html')

@app.route("/try.html",methods=['POST','GET'])
def fetch_url():
    #code for fetching the text
    url_regex=r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    if request.method=='POST':
        global text
        global predicted_op
        try:
            text=request.form['Text']
        except:
            check_db()
            #return render_template('test.html',error_message='Oops something went wrong.Please try again.')
        if text and text.isnumeric()==False and bool(re.match(url_regex,text))==True:
            try:
                show_working_msg()
                scraped=scraping_func_bs4(text)
                output,probability=ml_model(scraped)
                done=True
                if output[0]=='neither':
                    safe=True
                    predicted_op="Safe"
                    return render_template('try.html',safe=safe,done=done,probability=probability)
                elif output[0]=='hate_speech':
                    hate=True
                    predicted_op="Hate"
                    #return render_template('try.html',msg=f"This page may contain: Hate speech {(probability[0][0]*100):.2f} % likely",sc=scraped)
                    return render_template('try.html',hate=hate,done=done,probability=probability)
                else:
                    off=True
                    predicted_op="Offensive"
                    #return render_template('try.html',msg=f"This page may contain: Offensive Language {(probability[0][2]*100):.2f} % likely",sc=scraped)
                    return render_template('try.html',done=done,probability=probability,off=off)
            except:
                show_need_more_time()
                global scraped_text
                scraped_text=scraping_func_selenium(text)
                output,probability=ml_model(scraped_text)
                done=True
                if output[0]=='neither':
                    safe=True
                    predicted_op="Safe"
                    return render_template('try.html',safe=safe,done=done,probability=probability)
                elif output[0]=='hate_speech':
                    hate=True
                    predicted_op="Hate"
                #return render_template('try.html',msg=f"This page may contain: Hate speech {(probability[0][0]*100):.2f} % likely",sc=scraped_text)
                    return render_template('try.html',hate=hate,done=done,probability=probability)
                else:
                    off=True
                    predicted_op="Offensive"
                #return render_template('try.html',msg=f"This page may contain: Offensive Language {(probability[0][2]*100):.2f} % likely",sc=scraped_text)
                    return render_template('try.html',done=done,probability=probability,off=off)
        elif text:
            #call ml_model func
            output,probability=ml_model(text)
            done=True
            if output[0]=='neither':
                safe=True
                predicted_op="Safe"
                return render_template('try.html',safe=safe,done=done,probability=probability)
            elif output[0]=='hate_speech':
                hate=True
                predicted_op="Hate"
                #return render_template('try.html',msg=f"This page may contain: Hate speech {(probability[0][0]*100):.2f} % likely")
                return render_template('try.html',hate=hate,done=done,probability=probability)

            else:
                off=True
                predicted_op="Offensive"
                #return render_template('try.html',msg=f"This page may contain: Offensive Language {(probability[0][2]*100):.2f} % likely")
                return render_template('try.html',done=done,probability=probability,off=off)
    #if request.method=='POST':
        #if request.form['button']=='Yes':
            #feedback_to_db(predicted_op)
        #if request.form['button']=='No':
            #feedback_to_db()
        #return Response(response=json.loads({name:"X",age:"y"}),status=200,mimetype="application/json")
        #test_db()
        #return Response(response=json.loads({name:"X",age:"y"}),status=200,mimetype="application/json")
        #feedback_to_db(predicted_op)
    
if __name__ == "__main__":
    app.run(debug=True)
