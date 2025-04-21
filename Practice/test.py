import streamlit as st
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
import pandas as pd
import json
from datetime import datetime
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import plotly.express as px  # Plotly Express를 함수 내부에서 임포트
from wordcloud import WordCloud
font_path = 'C:\\windows\\Fonts\\malgun.ttf'
font_prop = fm.FontProperties(fname=font_path).get_name()
matplotlib.rc('font', family=font_prop)
PREFIX = {}
SUFFIX = {}
st.set_page_config(
    page_title="사람인 채용 정보 크롤러",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)
tab1, tab2 = st.tabs(["채용공고", "분석"])
# 산업군 카테고리와 각 카테고리별 키워드 매핑
industry_keywords = {
    "서비스업": ["고객 서비스", "판매", "서비스", "영업", "상담", "CS", "A/S"],
    "제조/화학": ["제조", "생산", "화학", "기계", "공장", "품질", "생산관리"],
    "의료/제약/복지": ["의료", "간호", "약사", "의사", "제약", "복지", "건강", "병원", "보험"],
    "유통/무역/운송": ["유통", "물류", "운송", "무역", "수출", "수입", "창고"],
    "교육업": ["교사", "교육", "학원", "강사", "학습", "학생", "교육기관"],
    "건설업": ["건설", "토목", "건축", "시설", "건축사", "건설현장", "설계"],
    "IT/웹/통신": ["개발", "프로그래밍", "소프트웨어", "하드웨어", "웹", "통신", "IT", "네트워크", "C", "Java", "AI", "API", "Android", "DB", ],
    "미디어/디자인": ["디자인", "그래픽", "영상", "미디어", "홍보", "광고", "마케팅", "아트", "ART"],
    "은행/금융업": ["은행", "금융", "회계", "세무", "투자", "대출", "자산관리"],
    "기관/협회": ["기관", "협회", "NGO", "정부", "비영리", "행정", "사회복지"]
}

# ✅ 산업군 이름-코드 매핑
industry_map = {
    "서비스업": 100,
    "제조/화학": 200,
    "의료/제약/복지": 300,
    "유통/무역/운송": 400,
    "교육업": 500,
    "건설업": 600,
    "IT/웹/통신": 700,
    "미디어/디자인": 800,
    "은행/금융업": 900,
    "기관/협회": 1000
}
# 잡플래닛 지역 매핑
score_region = {
    "서울" : 1,
    "경기" : 2,
    "인천" : 3,
    "부산" : 4,
    "대구" : 5,
    "대전" : 6,
    "광주" : 7,
    "울산" : 8,
    "세종" : 9,
    "강원" : 10,
    "경남" : 11,
    "경북" : 12,
    "전남" : 13,
    "전북" : 14,
    "충남" : 15,
    "충북" : 16,
    "제주" : 17
}

# 직무에 맞는 산업군 매핑 함수
def map_job_to_industry(job):
    for industry, keywords in industry_keywords.items():
        for keyword in keywords:
            if keyword in job:
                return industry
    return "기타"  # 키워드가 없으면 기타로 분류

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
    # print(selected_subregions)
    # if selected_subregions == ['전체']:
    #     print(selected_region)
    #     selected_region = selected_region[0]
    #     print(selected_region)

    
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
    if not isinstance(exp, str) or not exp.strip():
        return "정보 없음"

    exp = exp.strip()
    if '신입' in exp and '경력' in exp:
        return '신입/경력'
    elif '신입' in exp:
        return '신입'
    elif '경력무관' in exp or '년수무관' in exp:
        return '경력무관'
    elif re.match(r'\d+\s*~\s*\d+년', exp):
        return exp.replace(' ', '')
    elif re.match(r'\d+년\s*이상', exp):
        return exp
    elif re.match(r'\d+년\s*이하', exp):
        return exp
    elif exp == '경력':
        return '경력'
    return "정보 없음"

def normalize_education(education):
    if not isinstance(education, str):
        return None
    return education.replace('↑', '').strip()

def calculate_remaining_days(deadline):
    if not isinstance(deadline, str) or "채용시" in deadline or "마감" in deadline:
        return "기간 없음"

    if deadline.startswith("D-"):
        try:
            remaining_days = int(deadline[2:])
            if remaining_days < 0:
                return "마감"
            return f"{remaining_days}일 남음"
        except ValueError:
            return "기간 없음"

    if deadline.startswith("~"):
        try:
            match = re.search(r'~(\d{2})\.(\d{2})', deadline)
            if match:
                month, day = int(match.group(1)), int(match.group(2))
                current_year = datetime.now().year
                deadline_date = datetime(current_year, month, day)
                remaining_days = (deadline_date - datetime.now()).days
                if remaining_days < 0:
                    return "마감"
                return f"{remaining_days}일 남음"
            return "기간 없음"
        except ValueError:
            return "기간 없음"

    if "시 마감" in deadline:
        try:
            match = re.search(r'(\d{1,2})시', deadline)
            if match:
                hour = int(match.group(1))
                now = datetime.now()
                deadline_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                if deadline_time < now:
                    return "마감"
                remaining_seconds = (deadline_time - now).total_seconds()
                remaining_hours = remaining_seconds // 3600
                return f"{int(remaining_hours)}시간 남음"
            return "기간 없음"
        except ValueError:
            return "기간 없음"

    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
        remaining_days = (deadline_date - datetime.now()).days
        if remaining_days < 0:
            return "마감"
        return f"{remaining_days}일 남음"
    except ValueError:
        return "기간 없음"

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
                '제목': extract_text("div.job_tit span"),
                '직무': [tag.text.strip() for tag in item.select(".job_sector span") if tag.text.strip()],
                '지역': extract_text(".recruit_info .work_place").rstrip(' 외'),
                '요구경력': extract_text(".recruit_info .career"),
                '최소학력': extract_text(".recruit_info .education"),
                '기간': extract_text("span.date"),
                '링크': extract_href("div.job_tit a.str_tit"),
                '회사': extract_text("div.col.company_nm .str_tit"),
                '회사링크': extract_href("div.col.company_nm a.str_tit"),
                '등록일자': extract_text("span.deadlines"),
                '배지': extract_text(".job_badge span")
            })

    df = pd.DataFrame(results)
    if not df.empty:
        df[['요구경력_raw', '계약종류']] = df['요구경력'].apply(split_info)
        df['요구경력'] = df['요구경력_raw'].apply(normalize_experience)
        df['최소학력'] = df['최소학력'].apply(normalize_education)
        df['남은기간'] = df['기간'].apply(calculate_remaining_days)
        df.drop(columns=['요구경력_raw'], inplace=True)
        df.dropna(axis=0, inplace=True)
    return df

def filter_by_experience(df, exp_input, include_general):
    
    def parse_year_range(exp_text):
        match = re.search(r'(\d+)\s*~\s*(\d+)', exp_text)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r'(\d+)\s*년\s*이상', exp_text)
        if match:
            return int(match.group(1)), float('inf')
        match = re.search(r'(\d+)\s*년\s*이하', exp_text)
        if match:
            return 0, int(match.group(1))
        match = re.search(r'경력\s*(\d+)\s*년', exp_text)
        if match:
            return int(match.group(1)), int(match.group(1))
        return None, None

    general_conditions = ['신입', '신입/경력', '경력무관', '정보 없음']

    try:
        exp_val = int(re.search(r'\d+', exp_input.strip()).group()) if exp_input.strip() else None
    except AttributeError:
        st.warning("⚠️ 경력 입력이 올바르지 않습니다. 기본 필터만 적용합니다.")
        return df[df['요구경력'].isin(general_conditions) if include_general else []]

    filtered_rows = []

    for _, row in df.iterrows():
        exp = row['요구경력']
        min_exp, max_exp = parse_year_range(exp)

        # Include general conditions if 'include_general' is True
        if include_general and exp in general_conditions:
            filtered_rows.append(row)
        # Add rows matching the experience range
        if min_exp is not None and exp_val is not None and exp_val >= min_exp:
            filtered_rows.append(row)

    # Filtered DataFrame
    filtered_df = pd.DataFrame(filtered_rows)

    return filtered_df
    
def star_score(job_code, selected_region):
    # ✅ 크롬 옵션 설정
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    # ✅ 드라이버 실행
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # ✅ URL 설정
    base_url = f"https://www.jobplanet.co.kr/companies?sort_by=review_compensation_cache&industry_id={job_code}&city_id={score_region[selected_region]}"

    companies = []
    page = 1

    while True:
        url = f"{base_url}&page={page}"
        driver.get(url)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        company_blocks = soup.select("div.section_wrap div.section_group section.company")
        # if page == 10:
        #     break
        if not company_blocks:
            print(f"❗ 페이지 {page}에 더 이상 항목이 없습니다. 크롤링 종료.")
            break

        for item in company_blocks:
            name_tag = item.select_one("dt.us_titb_l3 a")
            rating_tag = item.select_one("div.us_star_m div.star_score")

            if name_tag and rating_tag:
                name = name_tag.get_text(strip=True)
                rating_style = rating_tag.get("style", "")
                try:
                    width_pct = float(rating_style.replace("width:", "").replace("%", "").strip())
                    rating = round(width_pct / 20, 1)
                except:
                    rating = None

                companies.append({
                    "회사명": name,
                    "평점": rating
                })

        print(f"✅ {page}페이지 완료, 누적 기업 수: {len(companies)}")
        page += 1

    df = pd.DataFrame(companies)
    driver.quit();

    return df


def visualize_experience_distribution():
    st.subheader("경력 요구사항 분포")
    if st.session_state.all_jobs.empty:
        st.info("공고 데이터를 가져오세요.")
        return

    # 데이터 준비
    experience_counts = st.session_state.all_jobs['요구경력'].value_counts().reset_index()
    experience_counts.columns = ['요구경력', '공고수']

    # 원형 그래프 생성
    fig = px.pie(
        experience_counts,
        names='요구경력',
        values='공고수',
        title="경력 요구사항 분포",
        hole=0.3  # 도넛 형태로 변경
    )

    # 원형 그래프 스타일 설정 (복구)
    fig.update_traces(
        textinfo='percent+label',  # 퍼센트와 레이블 표시
        textfont_size=14,  # 폰트 크기
        insidetextorientation='radial',  # 텍스트 방향
        marker=dict(line=dict(width=0))  # 구분선 제거
    )

    # 그래프 출력
    st.plotly_chart(fig, use_container_width=True)

def visualize_education_distribution():
    st.subheader("최소 학력 요구 분포")
    if st.session_state.all_jobs.empty:
        st.info("공고 데이터를 가져오세요.")
        return

    # 데이터 준비
    education_counts = st.session_state.all_jobs['최소학력'].value_counts().reset_index()
    education_counts.columns = ['최소학력', '공고수']

    # 막대 그래프 생성
    fig = px.bar(
        education_counts,
        x='최소학력',
        y='공고수',
        title="최소 학력 요구 분포"
    )

    # 그래프 출력
    st.plotly_chart(fig, use_container_width=True)

def main_tab():
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
    if "favorites" not in st.session_state:
        st.session_state.favorites = pd.DataFrame()
    if "show_favorites" not in st.session_state:
        st.session_state.show_favorites = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1
    if "comp_score" not in st.session_state:
        st.session_state.comp_score = pd.DataFrame()

    if st.button("⭐ 나의 즐겨찾기"):
        st.session_state.show_favorites = not st.session_state.show_favorites

    if st.session_state.show_favorites:
        st.header("나의 즐겨찾기")
        if st.session_state.favorites.empty:
            st.info("즐겨찾기 목록이 비어 있습니다.")
        else:
            st.dataframe(st.session_state.favorites, use_container_width=True)

    with st.sidebar:
        st.header("대분류 지역 선택")
        selected_region = st.selectbox("대분류 지역", list(region_subregion_map.keys()))

        st.header("세부 지역 선택 (필수)")
        subregions = region_subregion_map[selected_region]
        # subregions = set()
        # for sub_region in selected_region:
        #     for temp in region_subregion_map[sub_region]:
        #         subregions.add(temp) 
        selected_subregions = st.multiselect("세부 지역", subregions)

        if st.button("공고 가져오기"):
            if not selected_subregions:
                st.warning("🚨 세부 지역을 하나 이상 선택해주세요.")
                st.stop()

            with st.spinner("데이터를 가져오는 중..."):
                st.session_state.all_jobs = crawl_jobs(10, selected_region, selected_subregions)
                st.session_state.filtered_jobs = st.session_state.all_jobs.copy()
                st.session_state.current_page = 1
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
                if st.button("평점 가져오기"):
                    job_industry_mapping = {job: map_job_to_industry(job) for job in selected_jobs}
                    industry_name = list(job_industry_mapping.values())[0]
                    print(industry_name)
                    industry_code = industry_map.get(industry_name)
                    
                    st.session_state.comp_score = star_score(industry_code, selected_region)
            comp_input = st.text_input("평점을 확인할 기업을 입력하세요\.", "")
            if comp_input:
                matched = st.session_state.comp_score[
                    st.session_state.comp_score['회사명'].str.contains(comp_input, na=False)
                ]
                if matched.empty:
                    st.info("해당 기업에 대한 평점 정보가 없습니다.")
                else:
                    st.dataframe(matched, use_container_width=True)
            st.header("요구 경력 필터")
            include_general = st.checkbox("경력무관 포함", value=True)
            experience_input = st.text_input("경력을 입력하세요 (예: 0, 숫자 또는 신입)", "")

            if experience_input or include_general:
                filtered_df = filter_by_experience(filtered_df, experience_input, include_general)
                if filtered_df.empty:
                    st.warning("해당 공고가 없습니다.")
                else:
                    st.success(f"{len(filtered_df)}개의 공고가 필터링되었습니다.")

            st.header("학력 필터")
            if '최소학력' not in filtered_df.columns:
                st.warning("🚫 '학력' 데이터가 없습니다. 필터를 사용할 수 없습니다.")
            else:
                unique_educations = filtered_df['최소학력'].dropna().unique()
                selected_educations = st.multiselect("학력을 선택하세요", ["전체"] + list(unique_educations))
                filtered_df = filter_by_education(filtered_df, selected_educations)

            st.session_state.filtered_jobs = filtered_df

    if not st.session_state.filtered_jobs.empty:
        st.header("검색 결과")

        jobs_per_page = 20
        total_jobs = len(st.session_state.filtered_jobs)
        total_pages = (total_jobs + jobs_per_page - 1) // jobs_per_page

        start_idx = (st.session_state.current_page - 1) * jobs_per_page
        end_idx = start_idx + jobs_per_page
        page_jobs = st.session_state.filtered_jobs.iloc[start_idx:end_idx]

        for idx, row in page_jobs.iterrows():
            with st.container():
                st.markdown("---")
                col1, col2 = st.columns([9, 1])

                with col1:
                    st.markdown(f"### **[{row['제목']}]({row['링크']})**")
                    st.markdown(f"- **회사**: [{row['회사']}]({row['회사링크']})")
                    st.markdown(f"- **직무**: {', '.join(row['직무'])}")  # 직무 수정된 부분
                    st.markdown(f"- **지역**: {row['지역']}")
                    st.markdown(f"- **경력**: {row['요구경력']}")
                    st.markdown(f"- **학력**: {row['최소학력']}")

                    if "마감" in row['남은기간']:
                        st.markdown(f"- **남은 기간**: <span style='color:red'>{row['남은기간']}</span>", unsafe_allow_html=True)
                    elif "시간 남음" in row['남은기간']:
                        st.markdown(f"- **남은 기간**: <span style='color:orange'>{row['남은기간']}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"- **남은 기간**: <span style='color:green'>{row['남은기간']}</span>", unsafe_allow_html=True)

                with col2:
                    if st.button("⭐", key=f"fav_{idx}"):
                        if not st.session_state.favorites.empty and row.to_dict() in st.session_state.favorites.to_dict('records'):
                            st.session_state.favorites = st.session_state.favorites[st.session_state.favorites['제목'] != row['제목']]
                            st.warning("즐겨찾기에서 제거되었습니다.")
                        else:
                            st.session_state.favorites = pd.concat([st.session_state.favorites, pd.DataFrame([row])], ignore_index=True)
                            st.success("즐겨찾기에 추가되었습니다!")

        col1, col2, col3 = st.columns(3)
        if st.session_state.current_page > 1:
            if col1.button("이전 페이지"):
                st.session_state.current_page -= 1
        col2.write(f"페이지 {st.session_state.current_page} / {total_pages}")
        if st.session_state.current_page < total_pages:
            if col3.button("다음 페이지"):
                st.session_state.current_page += 1

def visualize_job_distribution():
    st.subheader("지역별 직무 분포 (트리맵)")
    if st.session_state.all_jobs.empty:
        st.info("공고 데이터를 가져오세요.")
        return

    # 데이터 준비
    job_region_df = st.session_state.all_jobs.explode('직무')[['지역', '직무']]
    job_region_counts = job_region_df.groupby(['지역', '직무']).size().reset_index(name='공고수')

    # 트리맵 생성
    fig = px.treemap(
        job_region_counts,
        path=['지역', '직무'],  # 계층적 구조: 지역 > 직무
        values='공고수',
        title="지역별 직무 분포 (트리맵)"
    )

    # 트리맵 출력
    st.plotly_chart(fig, use_container_width=True)

def visual_word_cloud():
    dev_df = st.session_state.all_jobs[st.session_state.all_jobs['제목'].str.contains('개발', na=False)]
    df_exploded = dev_df.explode('직무')
    job_counts = df_exploded['직무'].value_counts()

    wordcloud = WordCloud(font_path=font_path, width=800, height=400, background_color='white', colormap='viridis')
    wordcloud.generate_from_frequencies(job_counts.to_dict())

    plt.figure(figsize=(18, 20))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')

    st.pyplot(plt)
    plt.clf()  # Streamlit에서 여러 번 출력할 때 이전 그래프 클리어

# 지역별 공고수 분석을 시각화 함수로 분리
def visual_chart_count():
    
    
    # 지역별 채용 공고수 집계
    job_counts = st.session_state.all_jobs['지역'].value_counts().reset_index()
    job_counts.columns = ['지역', '공고수']

    # 막대 그래프 출력 (표 위로 이동)
    st.subheader("지역별 채용 공고수 시각화")
    fig = px.bar(
        job_counts,
        x='지역',
        y='공고수',
        title='지역별 채용 공고수',
        color='공고수',  # 공고수에 따라 색상 변환
        labels={'지역': '지역', '공고수': '채용 공고수'},
        text='공고수'  # 막대 위에 공고수 표시
    )
    fig.update_traces(
        texttemplate='%{text}',  # 텍스트 형식
        textposition='outside',  # 텍스트 위치
        marker=dict(line=dict(color='black', width=1.5))  # 막대 테두리 추가
    )
    fig.update_layout(
        title=dict(font=dict(size=20), x=0.5),  # 제목 가운데 정렬
        xaxis=dict(title='지역', tickangle=45),  # X축 레이블 각도 조정
        yaxis=dict(title='채용 공고수', gridcolor='lightgray'),  # Y축 그리드 색상 조정
        plot_bgcolor='white'  # 배경 색상 흰색
    )
    st.plotly_chart(fig, use_container_width=True)

    # 표 출력 (막대 그래프 아래로 이동)
    st.subheader("지역별 채용 공고수")
    st.dataframe(job_counts, use_container_width=True)

def visual_chart_exp():
    plt.figure(figsize=(10, 6))
    plt.figure(figsize=(10, 6))
    
#     # '개발' 키워드가 포함된 공고만 필터링
    dev_df = st.session_state.all_jobs[st.session_state.all_jobs['제목'].str.contains('개발', na=False)]
    
    # 카운트 플롯
    sns.countplot(data=dev_df, x='요구경력', order=dev_df['요구경력'].value_counts().index)
    plt.title('개발자 요구 경력 분포')
    plt.xlabel('요구 경력')
    plt.ylabel('공고 수')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Streamlit에 출력
    st.pyplot(plt)
    plt.clf()  # Streamlit에서 여러 번 출력할 때 이전 그래프 클리어

def visual_piechart():
    contract_counts = st.session_state.all_jobs['계약종류'].value_counts()

    fig = px.pie(
        names=contract_counts.index,
        values=contract_counts.values,
        title='계약 종류별 공고 수 분포',
        hole=0.3
    )

    fig.update_traces(
        textinfo='percent+label',
        textposition='outside',        # 바깥에 라벨 표시
        rotation=120,                  # 시작 각도 설정
        pull=[0.05] * len(contract_counts),  # 항목 살짝 분리
    )

    fig.update_layout(
        showlegend=True,
        title=dict(font=dict(size=20), x=0),
        uniformtext_minsize=10,        # 너무 작은 텍스트는 생략
        uniformtext_mode='hide',
        height=600,                    # 차트 크기 키우기
        width=800,
    )

    st.plotly_chart(fig, use_container_width=True)


def visual_tab():
    # 📊 분석 탭 내용
    st.title("📊 지역별 채용 공고수 분석")
    if st.session_state.all_jobs.empty:
        st.warning("먼저 '공고 가져오기' 버튼을 눌러 데이터를 가져오세요.")
        return
    # 시각화 함수 호출
    visual_chart_count()
    visual_chart_exp()
    visual_piechart()
    visual_word_cloud()

    visualize_job_distribution()
    visualize_experience_distribution()
    visualize_education_distribution()
    


def main():
    with tab1:
        main_tab()
    with tab2:
        visual_tab()
# 최소 학력 필터 함수 추가
def filter_by_education(df, selected_educations):
    """
    Filters the DataFrame based on the selected education levels.
    If "전체" is selected, no filtering is applied.
    """
    if not isinstance(selected_educations, (list, pd.Series)):
        selected_educations = [selected_educations]
    
    # "전체" 선택 시 필터링 없이 반환
    if not selected_educations or "전체" in selected_educations:
        return df
    # 선택된 학력 조건에 맞는 데이터만 필터링
    return df[df['최소학력'].isin(selected_educations)]

if __name__ == "__main__":
    main()