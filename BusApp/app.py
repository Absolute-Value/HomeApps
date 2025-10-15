import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

PAGE_TITLE = 'バス情報'
BASE_URL = 'https://transfer-cloud.navitime.biz'
APPROACH_URL = f'{BASE_URL}/entetsu/approachings'
URL = f"{BASE_URL}/entetsu/trips"
STOPS = {
    '浜松駅': "00460001",
    'JR浜松工場': "00460074",
    '瑞生寺': "00460073",
    '西高入口': "00460072",
    '伊場遺跡入口': "00460071",
    '商工会議所': "00460070",
    '東伊場': "00460069",
    '菅原': "00460068",
    '成子坂西': "00460067",
    '成子坂': "00460066",
    '旅籠町': "00460065",
    'ザザシティ前': "00460064",
}
stops_list = list(STOPS.keys())

# メモリ内にデータを保存するための辞書
bus_data_cache = {}
cache_date = None

def get_approach_data(departure_stop, arrival_stop):
    """接近情報を取得"""
    params = {
        "departure-busstop": STOPS[departure_stop],
        "arrival-busstop": STOPS[arrival_stop],
    }
    resp = requests.get(APPROACH_URL, params=params)
    soup = BeautifulSoup(resp.text, "html.parser")

    approach_items = []
    bound_for_items = []
    pole_items = []
    pole_map_items = []
    
    rows = soup.find_all("button", class_=lambda x: x and 'rounded' in x and 'drop-shadow-md' in x)
    for row in rows:
        approach_elem = row.find('div', class_='text-lg my-3 text-center font-bold text-error')
        bound_for_elem = row.find('span', class_='font-bold')
        pole_elem = row.find('dt')
        map_elem = row.find('a')
        
        if approach_elem:
            approach_items.append(approach_elem.get_text())
        if bound_for_elem:
            bound_for_items.append(bound_for_elem.get_text())
        if pole_elem:
            pole_items.append(pole_elem.get_text().lstrip('のりば: '))
        if map_elem and map_elem.get('href'):
            pole_map_items.append(BASE_URL + map_elem.get('href'))
        else:
            pole_map_items.append('')
    
    return list(zip(approach_items, bound_for_items, pole_items, pole_map_items))

def get_bus_schedule(departure_stop, arrival_stop):
    """バス時刻表を取得"""
    global bus_data_cache, cache_date
    
    today = datetime.now().strftime("%Y-%m-%d")
    from_to = f'{departure_stop}_{arrival_stop}'
    
    if from_to not in bus_data_cache or cache_date != today:
        params = {
            "departure-busstop": STOPS[departure_stop],
            "arrival-busstop": STOPS[arrival_stop],
            "date": today
        }
        resp = requests.get(URL, params=params)
        soup = BeautifulSoup(resp.text, "html.parser")

        time_elems = soup.find_all("div", class_="mx-4 my-2 flex flex-col items-end")
        way_elems = soup.find_all("div", class_="flex flex-col")
        pole_elems = soup.find_all("a", class_="mr-2 block")
        all_stop_elems = soup.find_all("a", class_="mr-4")

        departure_times = []
        arrival_times = []
        durings = []
        ways = []
        pole_nums = []
        all_stop_urls = []
        
        for i, time_elem in enumerate(time_elems):
            time_tags = time_elem.find_all("time")
            if len(time_tags) >= 2:
                departure_times.append(time_tags[0].get_text(strip=True))
                arrival_times.append(time_tags[1].get_text(strip=True))
                
            duration_elem = time_elem.find("span", class_="text-text-grey")
            durings.append(duration_elem.get_text(strip=True) if duration_elem else '')
            
            if i < len(way_elems):
                way_elem = way_elems[i].find("span", class_="font-bold")
                ways.append(way_elem.get_text(strip=True) if way_elem else '')
            
            if i < len(pole_elems):
                pole_nums.append(pole_elems[i].get_text(strip=True))
                
            if i < len(all_stop_elems):
                all_stop_urls.append(BASE_URL + all_stop_elems[i]["href"])

        schedule_data = list(zip(departure_times, arrival_times, durings, ways, pole_nums, all_stop_urls))
        
        # 現在時刻から30分前以降のデータのみ保持
        cur_time = datetime.now()
        filtered_schedule = []
        for dep_time, arr_time, during, way, pole, url in schedule_data:
            try:
                dep_datetime = datetime.strptime(f'{today} {dep_time}', '%Y-%m-%d %H:%M')
                if dep_datetime > cur_time - timedelta(minutes=30):
                    filtered_schedule.append((dep_time, arr_time, during, way, pole, url))
            except ValueError:
                continue
        
        bus_data_cache[from_to] = filtered_schedule
        cache_date = today
    
    return bus_data_cache[from_to]

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, departure: int = 0, arrival: int = 1):
    """メインページ"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # デフォルトの表示（検索前）
    template_data = {
        "request": request,
        "page_title": PAGE_TITLE,
        "today": today,
        "stops": stops_list,
        "selected_departure": departure,
        "selected_arrival": arrival
    }
    
    # 検索パラメータがある場合はバス検索を実行
    if request.url.query and departure != arrival:
        departure_stop = stops_list[departure]
        arrival_stop = stops_list[arrival]
        
        try:
            # 接近情報取得
            approach_data = get_approach_data(departure_stop, arrival_stop)
            
            # 時刻表データ取得
            schedule_data = get_bus_schedule(departure_stop, arrival_stop)
            
            template_data.update({
                "departure_stop": departure_stop,
                "arrival_stop": arrival_stop,
                "approach_data": approach_data,
                "schedule_data": schedule_data
            })
        except Exception as e:
            template_data["error"] = "データの取得に失敗しました"
    
    elif request.url.query and departure == arrival:
        template_data["error"] = "出発地と到着地が同じです"
    
    return templates.TemplateResponse("index.html", template_data)

@app.post("/search")
async def search(
    departure: int = Form(...),
    arrival: int = Form(...)
):
    """バス検索 - ルートページにリダイレクト"""
    return RedirectResponse(url=f"./?departure={departure}&arrival={arrival}", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8503)