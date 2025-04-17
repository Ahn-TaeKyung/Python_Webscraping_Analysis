# streamlit run streamlit_submit.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import json

# 페이지 설정
st.set_page_config(
    page_title="사람인 채용 정보 크롤러",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# JSON 파일 로드 함수
@st.cache_data
def load_json_data():
    file_path = 'data/'
    with open(file_path + 'PREFIX.json', 'r', encoding='utf-8') as f:
        PREFIX = json.load(f)
    with open(file_path + 'SUFFIX.json', 'r', encoding='utf-8') as f:
        SUFFIX = json.load(f)
    return PREFIX, SUFFIX

# 지역별 요청 파라미터 파싱 함수
@st.cache_data
def parse_data(PREFIX, SUFFIX):
    req_parameter = {
        district: PREFIX[region] + suffix[-3:]
        for region, districts in SUFFIX.items()
        for district, suffix in districts.items()
    }
    for region, districts in SUFFIX.items():
        if '전체' in districts:
            req_parameter[region] = PREFIX[region] + districts['전체'][-3:]

    req_parameter2 = {
        '지역별': 'domestic',
        '직업별': 'job-category',
        '역세권별': 'subway',
        'HOT100': 'hot100',
        '헤드헌팅': 'headhunting'
    }
    return req_parameter, req_parameter2

def parse_location_input(user_input):

    # 3. 지역명을 코드로 변환
    region_codes = []
    for region in user_input:
        code = req_parameter.get(region)
        if code:
            region_codes.append(code)
        else:
            print(f"경고: '{region}' 지역을 찾을 수 없습니다.")

    return "%2C".join(region_codes)

# 채용 정보 크롤링 함수
def crawl_jobs(region_type, page_index, region_code):
    results = []
    if region_code == None:
        loc_cd_param = 101000
    else:
        loc_cd_param = parse_location_input(region_code)
    for page in range(1, page_index):
        url = (
            f"https://www.saramin.co.kr/zf_user/jobs/list/{region_type}"
            f"?page={page}&loc_cd={loc_cd_param}&search_done=y&preview=y"
        )
        headers = {'user-agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        if not res.ok:
            st.error(f"요청 실패: {res.status_code}")
            continue

        soup = BeautifulSoup(res.text, 'html.parser')
        job_items = soup.select("div#default_list_wrap div.list_body div.box_item")

        for item in job_items:
            def extract_text(selector, default='Null'):
                tag = item.select_one(selector)
                return tag.text.strip() if tag else default

            def extract_href(selector, prefix="https://www.saramin.co.kr"):
                tag = item.select_one(selector)
                return prefix + tag['href'] if tag and 'href' in tag.attrs else 'NULL'

            results.append({
                '링크': extract_href("div.job_tit a.str_tit"),
                '회사링크': extract_href("div.col.company_nm a.str_tit"),
                '제목': extract_text("div.job_tit span"),
                '회사': extract_text("div.col.company_nm .str_tit"),
                '직무': ' / '.join(
                    span.get_text(strip=True)
                    for span in item.select(".job_sector span")
                ) or 'Null',
                '지역': extract_text(".recruit_info .work_place").rstrip(' 외'),
                '요구경력': extract_text(".recruit_info .career"),
                '최소학력': extract_text(".recruit_info .education"),
                '기간': extract_text("span.date"),
                '등록일자': extract_text("span.deadlines"),
                '배지': extract_text(".job_badge span"),
            })

    return pd.DataFrame(results)

def split_info(text):
    if not isinstance(text, str):
        return pd.Series([None, None])
    
    parts = re.split(r'\s*·\s*', text)

    if len(parts) >= 2:
        exp = ' · '.join(parts[:-1]).strip()
        job_type = re.sub(r'\s*외$', '', parts[-1].strip())
        return pd.Series([exp, job_type])
    else:
        return pd.Series([text.strip(), None])
    
def normalize_experience(exp):
    if not isinstance(exp, str):
        return None  # 또는 '기타', '불명' 등

    exp = exp.strip()
    if '신입' in exp and '경력' in exp:
        return '신입/경력'
    elif '신입' in exp:
        return '신입'
    elif '경력무관' in exp or '년수무관' in exp:
        return '경력무관'
    elif re.match(r'경력 \d+년↑', exp):
        years = re.findall(r'\d+', exp)[0]
        return f'{years}년 이상'
    elif re.match(r'경력 \d+년↓', exp):
        years = re.findall(r'\d+', exp)[0]
        return f'{years}년 이하'
    elif re.match(r'\d+ ~ \d+년', exp):
        return exp.replace(' ', '')
    elif exp == '경력':
        return '경력'
    else:
        return exp
    
def process_registration_date(text):
    if not isinstance(text, str):
        return None
    
    # '수정'과 '등록' 제거
    text = re.sub(r'\s*(수정|등록)\s*', '', text)
    
    # 'n시간 전'을 '당일'로 변경
    text = re.sub(r'\d+\s*시간\s*전', '당일', text)
    
    # 'n분 전'은 그대로 두기
    text = re.sub(r'\d+\s*분\s*전', '당일', text)
    
    return text.strip()

# 메인 앱

def main():
    st.title(":mag: 사람인 채용 정보 크롤러")
    st.markdown("""
        사람인 사이트에서 원하는 지역의 채용 정보를 크롤링합니다.  
        왼쪽 사이드바에서 지역 유형과 지역을 선택하세요.
    """)

    PREFIX, SUFFIX = load_json_data()
    global req_parameter
    global req_parameter2
    req_parameter, req_parameter2 = parse_data(PREFIX, SUFFIX)

    with st.sidebar:
        st.header("검색 설정")
        selected_region_type = st.selectbox("지역 유형 선택", list(req_parameter2.keys()), index=0)
        region_type_code = req_parameter2[selected_region_type]

        selected_regions = None
        region_code = ''
        if selected_region_type == '지역별':
            regions = sorted(req_parameter.keys())
            selected_regions = st.multiselect("지역 선택", regions, default=['서울'] if '서울' in regions else [])
            # region_code = [req_parameter.get(region, '') for region in selected_regions]

        search_button = st.button("채용 정보 가져오기", type="primary")

    if search_button:
        with st.spinner(f"{selected_regions or selected_region_type} 채용 정보를 가져오는 중..."):
            df = crawl_jobs(region_type_code, 10, selected_regions)

            # 데이터 전처리
            df['원문'] = df['요구경력']
            df[['요구경력_raw', '계약종류']] = df['원문'].apply(split_info)
            # 적용
            df['요구경력'] = df['요구경력_raw'].apply(normalize_experience)
            df.drop(columns=['요구경력_raw'], inplace=True)
            df['등록일자'] = df['등록일자'].apply(process_registration_date)
            df.dropna(axis = 0, inplace=True)

            if not df.empty:
                st.success(f"총 {len(df)}개의 채용 정보를 찾았습니다!")
                st.dataframe(df, use_container_width=True, hide_index=True, column_config={
                    "링크": st.column_config.LinkColumn("링크", help="채용 공고 페이지"),
                })

                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="CSV로 다운로드",
                    data=csv,
                    file_name=f'saramin_jobs_{selected_regions or selected_region_type}.csv',
                    mime='text/csv'
                )
            else:
                st.warning("해당 지역의 채용 정보를 찾을 수 없습니다.")

if __name__ == "__main__":
    main()
