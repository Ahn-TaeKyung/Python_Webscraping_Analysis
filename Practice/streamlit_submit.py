# streamlit run streamlit_submit.py
import streamlit as st
import requests
import bs4
import re
import pandas as pd
import json
import numpy as np
from bs4 import BeautifulSoup

# 페이지 설정
st.set_page_config(
    page_title="사람인 채용 정보 크롤러",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일 적용
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# local_css("style.css")  # 로컬 CSS 파일이 있다면 사용

# JSON 파일 로드 함수
@st.cache_data
def load_json_data():
    file_path = 'data/'
    with open(file_path + 'PREFIX.json', 'r', encoding='utf-8') as f:
        PREFIX = json.load(f)
    with open(file_path + 'SUFFIX.json', 'r', encoding='utf-8') as f:
        SUFFIX = json.load(f)
    return PREFIX, SUFFIX

# 데이터 파싱 함수
@st.cache_data
def parse_data(PREFIX, SUFFIX):
    req_parameter_nested = {
        region: {
            district: PREFIX[region] + suffix[-3:]
            for district, suffix in districts.items()
        }
        for region, districts in SUFFIX.items()
    }

    req_parameter = {}
    for region, districts in req_parameter_nested.items():
        if '전체' in districts:
            req_parameter[region] = districts['전체']
        for district, code in districts.items():
            req_parameter[district] = code

    req_parameter2 = {
        '지역별': 'domestic',
        '직업별': 'job-category',
        '역세권별': 'subway',
        'HOT100': 'hot100',
        '헤드헌팅': 'headhunting'
    }
    
    return req_parameter, req_parameter2

# 채용 정보 크롤링 함수
def crawl_jobs(region_type, page_index, region_code):
    job_link_list = []
    corp_link_list = []
    logo_list = []
    title_list =[]
    job_list = []
    corp_list = []
    local_list = []
    exp_list = []
    grad_list = []
    date_list = []
    badge_list = []
    upload_list = []
    for page in range(1,page_index):
        url = f"https://www.saramin.co.kr/zf_user/jobs/list/{region_type}?page={page}&loc_cd={region_code}&panel_type=&search_optional_item=n&search_done=y&panel_count=y&preview=y"
        print(url)
        req_header = {
            'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
        }

        res = requests.get(url, headers = req_header)
        res.encoding = 'utf-8'

        
        if res.ok:
            html = res.text
            soup = BeautifulSoup(html, 'html.parser') 
            # CSS 선택자
            a_tag_list = soup.select("div#default_list_wrap div.list_body div.box_item")
            # <a> 태그 리스트 순회하기    
            for a_tag in a_tag_list:
                # 링크
                job_link_dict = {}
                if a_tag.find("div", class_ ="job_tit").find("a", class_ = "str_tit") == None:
                    print(a_tag.find("div", class_ ="job_tit"))
                    job_link_dict['링크'] = 'NULL'
                else:
                    job_link_dict['링크'] = "https://www.saramin.co.kr" + a_tag.find("div", class_ ="job_tit").find("a", class_ = "str_tit")['href']
                job_link_list.append(job_link_dict)

                # 회사 링크
                corp_link_dict = {}
                if a_tag.find("div", class_ ="col company_nm").find("a", class_ = "str_tit") == None:
                    corp_link_dict['회사링크'] = 'NULL'
                else:
                    corp_link_dict['회사링크'] = "https://www.saramin.co.kr" + a_tag.find("div", class_ ="col company_nm").find("a", class_ = "str_tit")['href']
                corp_link_list.append(corp_link_dict)

                # 로고
                # logo_dict = {}
                # if len(a_tag.select("span.logo img[src*='banner_logo/company/logo_banner/']")) == 0:
                #     logo_dict['로고'] = 'Null'
                # else:
                #     img_url = a_tag.select("span.logo img[src*='banner_logo/company/logo_banner/']")
                #     logo_dict['로고'] = img_url[0]['src']
                # logo_list.append(logo_dict)

                # 제목
                title_dict = {}
                if len(a_tag.find("div", class_ ="col notification_info").find("div", class_ = "job_tit").select("span")) == 0:
                    title_dict['제목'] = 'Null'
                else:
                    title = a_tag.find("div", class_ ="col notification_info").find("div", class_ = "job_tit").select("span")[0].text
                    title_dict['제목'] = title
                title_list.append(title_dict)

                # 회사
                corp_dict = {}
                if len(a_tag.find("div", class_ ="col company_nm").find(class_ = "str_tit")) == 0:
                    corp_dict['회사'] = 'Null'
                else:
                    corp = a_tag.find("div", class_ ="col company_nm").find(class_ = "str_tit").text
                    corp_dict['회사'] = corp
                corp_list.append(corp_dict)
                clean_corp = []
                for item in corp_list:
                    clean_item = {key: re.sub(r'\s+', ' ', value).strip() for key, value in item.items()}
                    clean_corp.append(clean_item)
                
                # 직무
                job_dict = {}
                job = a_tag.select_one('.job_sector')
                if len(job) == 0:
                    job_dict['직무'] = 'Null'
                else:
                    jobs = [span.get_text(strip=True).replace('::before', '').strip() for span in job.find_all('span')]
                    job_dict['직무'] = jobs
                job_list.append(job_dict)
                
                # 지역, 경력, 학력
                temp = a_tag.find("div", class_ = "col recruit_info")
                local_dict = {}
                exp_dict = {}
                grad_dict = {}
                if len(temp) >= 3:
                    local_dict['지역'] = temp.find("p", class_ = "work_place").text
                    exp_dict['요구경력'] = temp.find("p", class_ = "career").text
                    grad_dict['최소학력'] = temp.find("p", class_ = "education").text
                else:
                    local_dict['지역'] = 'NULL'
                    exp_dict['요구경력'] = 'NULL'
                    grad_dict['최소학력'] = 'NULL'
                local_list.append(local_dict)
                exp_list.append(exp_dict)
                grad_list.append(grad_dict)

                for region in local_list:
                    if region['지역'].endswith(' 외'):
                        region['지역'] = region['지역'][:-2]

                # 기간
                date_dict = {}
                if len(a_tag.select("span.date")) == 0:
                    date_dict['기간'] = 'Null'
                else:
                    date = a_tag.select("span.date")[0].text
                    date_dict['기간'] = date
                date_list.append(date_dict)

                clean_date = []
                for item in date_list:
                    clean_item = {key: re.sub(r'\s+', ' ', value).strip() for key, value in item.items()}
                    clean_date.append(clean_item)

                # 등록일자
                upload_dict = {}
                if len(a_tag.select_one("span.deadlines")) == 0:
                    upload_dict['등록일자'] = 'Null'
                else:
                    upload = a_tag.select("span.deadlines")[0].text
                    upload_dict['등록일자'] = upload
                upload_list.append(upload_dict)

                # 배지
                badge_dict = {}
                if a_tag.select_one(".job_badge") == None:
                    badge_dict['배지'] = 'Null'
                else:
                    badge = a_tag.select_one(".job_badge").find("span").text
                    badge_dict['배지'] = badge
                badge_list.append(badge_dict)
                clean_badge = []
                for item in badge_list:
                    clean_item = {key: re.sub(r'\s+', ' ', value).strip() for key, value in item.items()}
                    clean_badge.append(clean_item)

        else:
            # 응답(response)이 Error 이면 status code 출력    
            print(f'에러 코드 1= {res.status_code}')

        
    combined_list = []
    for link, corp_link, title, corp, job, local, exp, grad, date, upload, badge in zip(job_link_list, corp_link_list,title_list, clean_corp, job_list, local_list, exp_list, grad_list, clean_date, upload_list, clean_badge):
        merged_dict = {}
        merged_dict.update(link)
        merged_dict.update(corp_link)
        merged_dict.update(title)
        merged_dict.update(corp)
        merged_dict.update(job)
        merged_dict.update(local)
        merged_dict.update(exp)
        merged_dict.update(grad)
        merged_dict.update(date)
        merged_dict.update(upload)
        merged_dict.update(badge)
        combined_list.append(merged_dict)


    df = pd.DataFrame(combined_list)
    return df
# 메인 앱
def main():
    st.title("🔍 사람인 채용 정보 크롤러")
    st.markdown("""
    사람인 사이트에서 원하는 지역의 채용 정보를 크롤링합니다.  
    왼쪽 사이드바에서 지역 유형과 지역을 선택하세요.
    """)
    
    # 데이터 로드
    PREFIX, SUFFIX = load_json_data()
    global req_parameter
    global req_parameter2
    req_parameter, req_parameter2 = parse_data(PREFIX, SUFFIX)

    
    # 사이드바 설정
    with st.sidebar:
        st.header("검색 설정")
        
        # 지역 유형 선택
        region_type_options = {
            '지역별': 'domestic',
            '직업별': 'job-category',
            '역세권별': 'subway',
            'HOT100': 'hot100',
            '헤드헌팅': 'headhunting'
        }
        selected_region_type = st.selectbox(
            "지역 유형 선택",
            options=list(region_type_options.keys()),
            index=0
        )
        region_type_code = region_type_options[selected_region_type]
        
        # 지역 선택
        if selected_region_type == '지역별':
            regions = list(req_parameter.keys())
            selected_region = st.selectbox(
                "지역 선택",
                options=regions,
                index=regions.index('서울') if '서울' in regions else 0
            )
            region_code = req_parameter[selected_region]
        else:
            region_code = ''
        
        # 검색 버튼
        search_button = st.button("채용 정보 가져오기", type="primary")
    
    # 메인 영역
    if search_button:
        with st.spinner(f"{selected_region if selected_region_type == '지역별' else selected_region_type} 채용 정보를 가져오는 중..."):
            df = crawl_jobs(region_type_code, 10, region_code)
            
            if not df.empty:
                st.success(f"총 {len(df)}개의 채용 정보를 찾았습니다!")
                
                # 데이터 표시
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        # "로고": st.column_config.ImageColumn("로고", help="회사 로고"),
                        "링크": st.column_config.LinkColumn("링크", help="채용 공고 페이지"),
                    }
                )
                
                # CSV 다운로드 버튼
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="CSV로 다운로드",
                    data=csv,
                    file_name=f'saramin_jobs_{selected_region if selected_region_type == "지역별" else selected_region_type}.csv',
                    mime='text/csv'
                )
            else:
                st.warning("해당 지역의 채용 정보를 찾을 수 없습니다.")

if __name__ == "__main__":
    main()