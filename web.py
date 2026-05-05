import requests
from bs4 import BeautifulSoup
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter


# 判斷是在 Vercel 還是本地
if os.path.exists('serviceAccountKey.json'):
    # 本地環境：讀取檔案
    cred = credentials.Certificate('serviceAccountKey.json')
else:
    # 雲端環境：從環境變數讀取 JSON 字串
    firebase_config = os.getenv('FIREBASE_CONFIG')
    cred_dict = json.loads(firebase_config)
    cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred)

from flask import Flask, render_template, request
from datetime import datetime
import random

app = Flask(__name__)

@app.route("/")
def index():
    link ="<h1>歡迎進入林苡琦的網站首頁</h1>"
    link+= "<a href = /mis>課程</a><hr>"
    link+= "<a href = /today>今天日期</a><hr>"
    link+= "<a href = /about>關於017</a><hr>"
    link+= "<a href = /welcome?u=苡琦&dep=靜宜資管>GET傳直</a><hr>"
    link+= "<a href = /account>POST傳直(帳號密碼)</a><hr>"
    link+= "<a href = /math>數學計算</a><hr>"
    link += "<a href=/cup>擲茭</a><hr>"
    link += "<a href=/search>讀取Firestore資料</a><hr>"
    link += "<a href=/read>查詢老師及其研究室</a><hr>"
    link += "<a href=/sp1>爬蟲</a><hr>"
    link += "<a href=/movie>電影更新日期</a><hr>"
    link += "<a href=/searchQ>電影查詢</a><hr>"
    link += "<a href=/road>JSON-十大肇事入口</a><hr>"
    link += "<a href=/WT>天氣預報</a><hr>"
    return link
@app.route("/WT", methods=["GET", "POST"])
def WT():
    if request.method == "POST":
        city = request.form["city"]
        city = city.replace("台","臺")

        url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization=rdec-key-123-45678-011121314&format=JSON&locationName=" + city
        Data = requests.get(url)
        data = json.loads(Data.text)

        if data["records"]["location"]:
            WeatherTitle = data["records"]["datasetDescription"]
            Weather = data["records"]["location"][0]["weatherElement"][0]["time"][0]["parameter"]["parameterName"]
            Rain = data["records"]["location"][0]["weatherElement"][1]["time"][0]["parameter"]["parameterName"]

            result = f"{city}：{Weather}，降雨機率 {Rain}%"
        else:
            result = "查無此縣市"

        return render_template("weather.html", result=result)

    return render_template("weather.html", result=None)

@app.route("/road")
def road():
    R=""
    url = " https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=a1b899c0-511f-4e3d-b22b-814982a97e41"
    Data = requests.get(url)
    
    JsonData = json.loads(Data.text)
    for item in JsonData:
        R+=item["路口名稱"]+",總共發生"+item["總件數"]+"件事故<br>"
    return R

@app.route("/searchQ", methods=["POST","GET"])
def searchQ():
    if request.method == "POST":
        MovieTitle = request.form["MovieTitle"]
        info = ""
        db = firestore.client()     
        collection_ref = db.collection("電影2A")
        docs = collection_ref.order_by("showDate").get()
        for doc in docs:
            if MovieTitle in doc.to_dict()["title"]: 
                info += "片名：" + doc.to_dict()["title"] + "<br>" 
                info += "影片介紹：" + doc.to_dict()["hyperlink"] + "<br>"
                info += "片長：" + doc.to_dict()["showLength"] + " 分鐘<br>" 
                info += "上映日期：" + doc.to_dict()["showDate"] + "<br><br>"           
        return info
    else:  
        return render_template("searchQ.html")

@app.route("/movie")
def movie():
  url = "http://www.atmovies.com.tw/movie/next/"
  Data = requests.get(url)
  Data.encoding = "utf-8"
  sp = BeautifulSoup(Data.text, "html.parser")
  result=sp.select(".filmListAllX li")
  lastUpdate = sp.find("div", class_="smaller09").text[5:]

  for item in result:
    picture = item.find("img").get("src").replace(" ", "")
    title = item.find("div", class_="filmtitle").text
    movie_id = item.find("div", class_="filmtitle").find("a").get("href").replace("/", "").replace("movie", "")
    hyperlink = "http://www.atmovies.com.tw" + item.find("div", class_="filmtitle").find("a").get("href")
    show = item.find("div", class_="runtime").text.replace("上映日期：", "")
    show = show.replace("片長：", "")
    show = show.replace("分", "")
    showDate = show[0:10]
    showLength = show[13:]

    doc = {
        "title": title,
        "picture": picture,
        "hyperlink": hyperlink,
        "showDate": showDate,
        "showLength": showLength,
        "lastUpdate": lastUpdate
      }

    db = firestore.client()
    doc_ref = db.collection("電影2A").document(movie_id)
    doc_ref.set(doc)    
  return "近期上映電影已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate 


@app.route("/sp1")
def sp1():
    R=""
    url = "https://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    #print(Data.text)
    sp = BeautifulSoup(Data.text, "html.parser")
    result=sp.select(".filmListAllX li")
    for item in result:
        # 获取电影名称和链接
        movie_name = item.find("img").get("alt")
        movie_link = "https://www.atmovies.com.tw" + item.find("a").get("href")
        
        # 创建一个可点击的链接并将其加入返回的 HTML
        R += f'電影:{movie_name}<br>連結:<a href="{movie_link}" target="_blank">{movie_link}</a><br><br>'
    
    return R

@app.route("/search")
def search():
    db = firestore.client()
    collection_ref = db.collection("靜宜資管2026a")
    docs = collection_ref.order_by("lab", direction=firestore.Query.DESCENDING).limit(4).get()
   
    Temp = "<h3>資料庫前四筆資料：</h3>"
    for doc in docs:
        Temp += str(doc.to_dict()) + "<br>"
    return Temp + "<br><a href=/>回到首頁</a>"

@app.route("/read", methods=["GET", "POST"])
def read():
    result = None

    if request.method == "POST":
        keyword = request.form["keyword"]
        temp = ""

        for doc in firestore.client().collection("靜宜資管2026a").get():
            data = doc.to_dict()

            if keyword in data["name"]:
                temp += f"""
                <p>老師姓名：{data["name"]}</p>
                <p>研究室：{data["lab"]}</p>
                <p>信箱：{data["mail"]}</p>
                <hr>
                """

        result = temp if temp else "查無資料"

    return render_template("read.html", result=result)

@app.route("/mis")
def course():
    return "<h1>資訊管理導論</h1><a href=/>回到網站首頁</a>"

@app.route("/today")
def today():
    now = datetime.now()
    year = str(now.year)
    month = str(now.month)
    day = str(now.day)
    now =year+"年"+month+"月"+day+"日"
    return render_template("today.html",datetime = now)

@app.route("/about")
def about():
    return render_template("mis2A.html")

@app.route("/welcome",methods=["GET"])
def welcome():
    x=request.values.get("u")
    y=request.values.get("dep")
    return render_template("welcome.html",name = x, dep = y)

@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pwd"]
        result = "您輸入的帳號是：" + user + "; 密碼為：" + pwd 
        return result
    else:
        return render_template("account.html")

@app.route("/math", methods=["GET", "POST"])
def math():
    result = None
    error = None

    if request.method == "POST":
        try:
            x = int(request.form["x"])
            y = int(request.form["y"])
            opt = request.form["opt"]

            if opt == "/" and y == 0:
                error = "除數不能為0"
            else:
                if opt == "+":
                    result = x + y
                elif opt == "-":
                    result = x - y
                elif opt == "*":
                    result = x * y
                elif opt == "/":
                    result = x / y

        except ValueError:
            error = "請輸入數字"

    return render_template("math.html", result=result, error=error)

@app.route('/cup', methods=["GET"])
def cup():
    # 檢查網址是否有 ?action=toss
    #action = request.args.get('action')
    action = request.values.get("action")
    result = None
    
    if action == 'toss':
        # 0 代表陽面，1 代表陰面
        x1 = random.randint(0, 1)
        x2 = random.randint(0, 1)
        
        # 判斷結果文字
        if x1 != x2:
            msg = "聖筊：表示神明允許、同意，或行事會順利。"
        elif x1 == 0:
            msg = "笑筊：表示神明一笑、不解，或者考慮中，行事狀況不明。"
        else:
            msg = "陰筊：表示神明否定、憤怒，或者不宜行事。"
            
        result = {
            "cup1": "/static/" + str(x1) + ".jpg",
            "cup2": "/static/" + str(x2) + ".jpg",
            "message": msg
        }
        
    return render_template('cup.html', result=result)

if __name__ == "__main__":
    app.run(debug=True)
