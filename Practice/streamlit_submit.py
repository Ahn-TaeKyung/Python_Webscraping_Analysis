# streamlit run streamlit_submit.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import json

st.set_page_config(
    page_title="사람인 채용 정보 크롤러",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_json_data():
    file_path = 'data/'
    with open(file_path + 'PREFIX.json', 'r', encoding='utf-8') as f:
        PREFIX = json.load(f)
    with open(file_path + 'SUFFIX.json', 'r', encoding='utf-8') as f:
        SUFFIX = json.load(f)
    return PREFIX, SUFFIX

@st.cache_data
def parse_data(PREFIX, SUFFIX):
    req_parameter = {}
    region_subregion_map = {}

    for region, subregions in SUFFIX.items():
        region_code_prefix = PREFIX.get(region)
        if not region_code_prefix:
            continue

        region_subregion_map[region] = list(subregions.keys())
        for subregion, suffix_code in subregions.items():
            key = f"{region} {subregion}"
            req_parameter[key] = region_code_prefix + suffix_code

    return req_parameter, region_subregion_map

def parse_location_input(selected_region, selected_subregions):
    region_codes = []

    for district in selected_subregions:
        key = f"{selected_region} {district}"
        code = req_parameter.get(key)

        if code:
            region_codes.append(code)
        else:
            st.warning(f"⚠️ 지역 코드 없음: '{key}'")
    
    return "%2C".join(region_codes)

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
        return None
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

def normalize_education(education):
    if not isinstance(education, str):
        return None
    education = education.strip()
    if '↑' in education:
        education = education.replace('↑', '')
    return education

def process_registration_date(text):
    if not isinstance(text, str):
        return None
    text = re.sub(r'\s*(수정|등록)\s*', '', text)
    text = re.sub(r'\d+\s*시간\s*전', '당일', text)
    text = re.sub(r'\d+\s*분\s*전', '당일', text)
    return text.strip()

def extract_job_sectors(item):
    sector_tags = item.select(".job_sector span")
    sectors = [tag.text.strip() for tag in sector_tags if "외" not in tag.text]
    return sectors

def crawl_jobs(page_index, selected_region, selected_subregions):
    results = []
    loc_cd_param = parse_location_input(selected_region, selected_subregions)
    for page in range(1, page_index + 1):
        url = (
            f"https://www.saramin.co.kr/zf_user/jobs/list/domestic"
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
                '직무': extract_job_sectors(item),
                '지역': extract_text(".recruit_info .work_place").rstrip(' 외'),
                '요구경력': extract_text(".recruit_info .career"),
                '최소학력': extract_text(".recruit_info .education"),
                '기간': extract_text("span.date"),
                '등록일자': extract_text("span.deadlines"),
                '배지': extract_text(".job_badge span"),
            })

    df = pd.DataFrame(results)
    print(df['직무'])
    if not df.empty:
        df[['요구경력_raw', '계약종류']] = df['요구경력'].apply(split_info)
        df['요구경력'] = df['요구경력_raw'].apply(normalize_experience)
        df['최소학력'] = df['최소학력'].apply(normalize_education)
        df['등록일자'] = df['등록일자'].apply(process_registration_date)
        df.drop(columns=['요구경력_raw'], inplace=True)
        df.dropna(axis=0, inplace=True)
        # df['직무'] = df['직무'].apply(lambda x: [job.strip() for job in x.split('/')])
    return df

# ✅ 경력 필터링 함수
def filter_by_experience(df, exp_input):
    def parse_year_range(exp_text):
        if '신입' in exp_text or '경력무관' in exp_text:
            return 0, 0
        elif '년 이상' in exp_text:
            year = int(re.findall(r'\d+', exp_text)[0])
            return year, float('inf')
        elif '년 이하' in exp_text:
            year = int(re.findall(r'\d+', exp_text)[0])
            return 0, year
        elif re.match(r'\d+~\d+년', exp_text):
            nums = list(map(int, re.findall(r'\d+', exp_text)))
            return nums[0], nums[1]
        return None, None

    if exp_input == '신입':
        return df[df['요구경력'].isin(['신입', '경력무관', '신입/경력'])]

    try:
        exp_val = int(exp_input)
    except ValueError:
        return df

    filtered_rows = []
    for _, row in df.iterrows():
        exp = row['요구경력']
        min_exp, max_exp = parse_year_range(exp)
        if min_exp is None:
            continue
        if min_exp <= exp_val <= max_exp:
            filtered_rows.append(row)

    return pd.DataFrame(filtered_rows)

def main():
    st.title(":mag: 사람인 채용 정보 크롤러")
    st.markdown("""사람인 사이트에서 원하는 지역의 채용 정보를 크롤링합니다.""")

    PREFIX, SUFFIX = load_json_data()
    global req_parameter
    global region_subregion_map
    req_parameter, region_subregion_map = parse_data(PREFIX, SUFFIX)

    if "all_jobs" not in st.session_state:
        st.session_state.all_jobs = pd.DataFrame()
    if "filtered_jobs" not in st.session_state:
        st.session_state.filtered_jobs = pd.DataFrame()

    with st.sidebar:
        st.header("대분류 지역 선택")
        selected_region = st.selectbox("대분류 지역", list(region_subregion_map.keys()))

        st.header("세부 지역 선택")
        subregions = region_subregion_map[selected_region]
        selected_subregions = st.multiselect("세부 지역", subregions)

        if st.button("공고 가져오기"):
            with st.spinner("데이터를 가져오는 중..."):
                st.session_state.all_jobs = crawl_jobs(10, selected_region, selected_subregions)
                st.session_state.filtered_jobs = st.session_state.all_jobs.copy()
                st.success(f"{len(st.session_state.all_jobs)}개의 공고를 가져왔습니다!")

        if not st.session_state.all_jobs.empty:
            st.header("필터")
            unique_jobs = sorted(set(
                job for job_list in st.session_state.all_jobs['직무'].dropna() if isinstance(job_list, list) for job in job_list
            ))
            selected_jobs = st.multiselect("직무 선택", unique_jobs)

            filtered_df = st.session_state.all_jobs.copy()
            if selected_jobs:
                filtered_df = filtered_df[filtered_df['직무'].apply(lambda x: any(job in x for job in selected_jobs))]

            # ✅ 경력 필터 입력 UI
            st.header("요구 경력 필터")
            experience_input = st.text_input("경력을 입력하세요 (예: 신입 또는 숫자)", "")

            if experience_input:
                filtered_df = filter_by_experience(filtered_df, experience_input)

            st.session_state.filtered_jobs = filtered_df

    if not st.session_state.filtered_jobs.empty:
        st.header("검색 결과")

        if st.button("새로고침"):
            st.session_state.all_jobs = pd.DataFrame()
            st.session_state.filtered_jobs = pd.DataFrame()
            st.experimental_rerun()

        st.dataframe(st.session_state.filtered_jobs, use_container_width=True, hide_index=True)

        csv = st.session_state.filtered_jobs.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="CSV로 다운로드",
            data=csv,
            file_name="filtered_jobs.csv",
            mime="text/csv"
        )
    else:
        st.warning("조건에 맞는 공고가 없습니다.")

if __name__ == "__main__":
    main()
