import requests, json
url = "	https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=a1b899c0-511f-4e3d-b22b-814982a97e41"
Data = requests.get(url)
#print(Data.text)
JsonData = json.loads(Data.text)
for item in JsonData:
	print(item["路口名稱"]+",總共發生"+item["總件數"]+"件事故")
	print()
