import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

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

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=':material/directions_bus:',
    layout='wide'
)
st.title(PAGE_TITLE)

cur_time = datetime.now()
today = cur_time.strftime("%Y-%m-%d")
st.write(today)
if "today" not in st.session_state:
    st.session_state["today"] = today

if 'indexes' not in st.session_state:
    st.session_state['indexes'] = [1,0]

@st.fragment
def station_form():
    container = st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center")
    st.session_state['indexes'][0] = container.selectbox(
        "出発",
        list(range(len(stops_list))),
        format_func=lambda option: stops_list[int(option)],
        index=st.session_state['indexes'][0],
        label_visibility="collapsed",
        width=200
    )
    container.text('から')
    st.session_state['indexes'][1] = container.selectbox(
        "到着",
        list(range(len(stops_list))),
        format_func=lambda option: stops_list[int(option)],
        index=st.session_state['indexes'][1],
        label_visibility="collapsed",
        width=200
    )
    if container.button("<->"):
        st.session_state['indexes'].reverse()
        st.rerun(scope="fragment")
station_form()

departure_busstop = stops_list[int(st.session_state['indexes'][0])]
arrival_busstop = stops_list[int(st.session_state['indexes'][1])]
from_to = f'{departure_busstop}_{arrival_busstop}'

if st.button("検索") and departure_busstop != arrival_busstop:
    params = {
        "departure-busstop": STOPS[departure_busstop],
        "arrival-busstop": STOPS[arrival_busstop],
    }
    resp = requests.get(APPROACH_URL, params=params)
    soup = BeautifulSoup(resp.text, "html.parser")

    approach_items = []
    bound_for_items = []
    pole_items = []
    pole_map_items = []
    rows = soup.find_all("button", class_=lambda x: x and 'rounded' in x and 'drop-shadow-md' in x)
    for row in rows:
        approach_items.append(row.find('div', class_='text-lg my-3 text-center font-bold text-error').get_text())
        bound_for_items.append(row.find('span', class_='font-bold').get_text())
        pole_items.append(row.find('dt').get_text().lstrip('のりば: '))
        pole_map_items.append(row.find('a'))
    
    approach_df = pd.DataFrame(
        {
            '接近情報': approach_items,
            '系統・行先': bound_for_items,
            'のりば': pole_items,
            'のりばマップ': pole_map_items,
        }
    )

    st.dataframe(
        approach_df,
        column_config={
            'のりばマップ': st.column_config.LinkColumn('のりばマップ', display_text='マップ'),
        },
        hide_index=True
    )

    if from_to not in st.session_state or st.session_state["today"] != today:
        params["date"] = today
        resp = requests.get(URL, params=params)
        soup = BeautifulSoup(resp.text, "html.parser")

        time_elems = soup.find_all("div", class_="mx-4 my-2 flex flex-col items-end")
        way_elems = soup.find_all("div", class_="flex flex-col")
        pole_elems = soup.find_all("a", class_="mr-2 block")
        all_stop_elems = soup.find_all("a", class_="mr-4")

        departure_times = [time_elem.find_all("time")[0].get_text(strip=True) for time_elem in time_elems]
        arrival_times = [time_elem.find_all("time")[1].get_text(strip=True) for time_elem in time_elems]
        durings = [time_elem.find("span", class_="text-text-grey").get_text(strip=True) for time_elem in time_elems]
        ways = [way_elem.find("span", class_="font-bold").get_text(strip=True) for way_elem in way_elems]
        pole_links = [BASE_URL + pole_elem["href"] for pole_elem in pole_elems]
        pole_nums = [pole_elem.get_text(strip=True) for pole_elem in pole_elems]
        all_stop_urls = [BASE_URL + all_stop_elem["href"] for all_stop_elem in all_stop_elems]

        st.session_state[from_to] = pd.DataFrame(
            {
                '出発時刻': departure_times,
                '到着時刻': arrival_times,
                '移動時間': durings,
                '系統・行先': ways,
                'のりば': pole_nums,
                'url': all_stop_urls,
            }
        )
        st.write('roloaded')

    st.session_state[from_to]['出発時刻_datetime'] = pd.to_datetime(st.session_state[from_to]['出発時刻'].apply(lambda x: f'{today} {x}'))
    st.session_state[from_to] = st.session_state[from_to][st.session_state[from_to]['出発時刻_datetime'] > cur_time - timedelta(minutes=30)]
    st.session_state[from_to] = st.session_state[from_to].drop(columns=['出発時刻_datetime'])
    st.dataframe(
        st.session_state[from_to],
        column_config={
            'url': st.column_config.LinkColumn('経路', display_text='通過時刻表'),
        },
        hide_index=True,
        height=500
    )