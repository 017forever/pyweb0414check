import requests
from bs4 import BeautifulSoup
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google import genai
from google.genai import types

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

from flask import Flask, render_template, request, make_response, jsonify
from datetime import datetime
import random

app = Flask(__name__)
client = genai.Client()


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
    link += "<a href=/rate>本週新片進DB</a><hr>"
    link += "<a href=/demo>聊天機器人</a><hr>"
    link += "<a href=/AI>AI試用</a><hr>"
    link += "<a href=/ask>真正的AI詢問</a><hr>"
    return link


@app.route('/ask', methods=['GET', 'POST']) 
def ask():
    if request.method == "POST":
        user_prompt = request.form.get('prompt', '')
        if not user_prompt:
            return "請輸入內容", 400
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=user_prompt,
            )
            return response.text
        except Exception as e:
            return f"發生錯誤: {str(e)}", 500

    else:    
        # 當使用者直接打開網頁 (GET) 時，顯示輸入框畫面
        return render_template("ask.html")


@app.route("/AI")
def AI():
    # 每次使用者拜訪該路徑時，直接使用全域的 client 呼叫模型
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents='我想查詢靜宜大學資管系的評價？',
    )
    
    # 回傳生成的文字
    return response.text



@app.route("/demo")
def demo():
    return render_template("demo.html")

@app.route("/webhook", methods=["POST"])
def webhook():

    req = request.get_json(force=True)
    action = req["queryResult"]["action"]

    if action == "rateChoice":
        rate = req["queryResult"]["parameters"]["rate"]
        info = "我是林苡琦設計的電影聊天機器人，您選擇的電影分級是：" + rate + "\n\n"

        db = firestore.client()
        collection_ref = db.collection("本週新片含分級")
        docs = collection_ref.get()

        result = ""

        for doc in docs:
            data = doc.to_dict()

            if rate == data["rate"]:
                result += "片名：" + data["title"] + "\n"
                result += "介紹：" + data["hyperlink"] + "\n\n"

        if result == "":
            result = "查無符合「" + rate + "」的電影"

        info += result

    elif (action == "input.unknown"):
        #info = req["queryResult"]["queryText"]
        # 2. 建立設定物件，設定你希望限制的最大 Token 數（例如 500）
        instruction_text = (
            "你是一個熱心且知識豐富的專業智慧助理。"
            "對於使用者的提問，請回覆重點的關鍵字，不要重述問題。"         
        )


        ai_config = types.GenerateContentConfig(
            max_output_tokens=500, 
            system_instruction=instruction_text
        )


        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=req["queryResult"]["queryText"],
            config=ai_config,
        )

        if response.text:
            info = response.text
        else:
            info = "抱歉，我現在無法生成回應，請稍後再試。"
    else:
        info = "我還不太懂你的意思"

    return make_response(jsonify({"fulfillmentText": info}))


@app.route("/rate")
def rate():
    #本週新片
    url = "https://www.atmovies.com.tw/movie/new/"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    Data = requests.get(url, headers=headers)
    Data.encoding = "utf-8"

    sp = BeautifulSoup(Data.text, "html.parser")

    update_tag = sp.find(class_="smaller09")
    if update_tag == None:
        return "找不到網站更新日期"

    lastUpdate = update_tag.text[5:]

    result = sp.select(".filmList")

    if len(result) == 0:
        return "沒有抓到電影資料，可能是 class 名稱錯了或網站格式改了"

    db = firestore.client()

    for x in result:
        runtime_tag = x.find(class_="runtime")
        if runtime_tag == None:
            continue

        a_tag = x.find("a")
        p_tag = x.find("p")

        if a_tag == None or p_tag == None:
            continue

        title = a_tag.text.strip()
        introduce = p_tag.text.strip()

        movie_id = a_tag.get("href").replace("/", "").replace("movie", "")
        hyperlink = "https://www.atmovies.com.tw/movie/" + movie_id
        picture = "https://www.atmovies.com.tw/photo101/" + movie_id + "/pm_" + movie_id + ".jpg"

        img_tag = runtime_tag.find("img")
        rate = ""

        if img_tag != None:
            rr = img_tag.get("src").replace("/images/cer_", "").replace(".gif", "")

            if rr == "G":
                rate = "普遍級"
            elif rr == "P":
                rate = "保護級"
            elif rr == "F2":
                rate = "輔12級"
            elif rr == "F5":
                rate = "輔15級"
            else:
                rate = "限制級"

        t = runtime_tag.text

        try:
            t1 = t.find("片長")
            t2 = t.find("分")
            showLength = t[t1+3:t2]

            t1 = t.find("上映日期")
            t2 = t.find("上映廳數")
            showDate = t[t1+5:t2-8]

            doc = {
                "title": title,
                "introduce": introduce,
                "picture": picture,
                "hyperlink": hyperlink,
                "showDate": showDate,
                "showLength": int(showLength),
                "rate": rate,
                "lastUpdate": lastUpdate
            }

            doc_ref = db.collection("本週新片含分級").document(movie_id)
            doc_ref.set(doc)

        except:
            print("這部電影資料格式有問題：", title)
            continue

    return "本週新片已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate



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
