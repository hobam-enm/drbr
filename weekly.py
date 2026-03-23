import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# ===== [ 1. 페이지 기본 설정 및 CSS 스타일링 ] =====
st.set_page_config(
    page_title="드라마 주간 브리핑",
    page_icon="🎬",
    layout="wide", # 너비를 넓게 쓰고 중앙에 1200px을 맞추기 위함
    initial_sidebar_state="expanded" # 사이드바를 기본으로 열어둠
)

st.markdown("""
<style>
    /* 상단 헤더 숨김 처리 */
    header[data-testid="stHeader"] { display: none !important; }
    
    /* 메인 화면 여백 최소화 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* 사이드바 라디오 버튼 디자인 튜닝 */
    div[data-testid="stSidebar"] div.row-widget.stRadio > div {
        gap: 10px;
    }
    div[data-testid="stSidebar"] div.row-widget.stRadio label {
        font-size: 16px !important;
        font-weight: 600 !important;
        padding: 10px 10px;
        background-color: #f8f9fa;
        border-radius: 8px;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    div[data-testid="stSidebar"] div.row-widget.stRadio label:hover {
        background-color: #e9ecef;
    }
</style>
""", unsafe_allow_html=True)


# ===== [ 2. 데이터 로드 (구글 시트 연동) ] =====
@st.cache_resource(ttl=600)
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def fetch_all_tabs(sheet_id: str):
    client = get_gspread_client()
    spreadsheet = client.open_by_key(sheet_id)
    
    # 시트에 있는 순서 그대로(왼쪽부터) 탭 목록을 가져옵니다.
    worksheets = spreadsheet.worksheets()
    
    tab_list = []
    for ws in worksheets:
        tab_list.append({
            "original_title": ws.title,
            # 요구사항: 탭 이름 뒤에 " 드라마 브리핑" 추가
            "display_title": f"{ws.title} 드라마 브리핑", 
            "gid": ws.id
        })
        
    return tab_list


# ===== [ 3. 메인 앱 실행 로직 ] =====
try:
    # 1. 시크릿에서 SHEET_ID를 가져와 탭 리스트 로드
    sheet_id = st.secrets["SHEET_ID"]
    all_tabs = fetch_all_tabs(sheet_id)
    
    if not all_tabs:
        st.warning("구글 시트에 탭이 없습니다.")
        st.stop()

    # 2. 사이드바 (좌측 1열 네비게이션)
    with st.sidebar:
        st.markdown("## 🗓️ 주간 브리핑 목록")
        st.divider()
        
        # 탭 이름들만 추출
        tab_titles = [t["display_title"] for t in all_tabs]
        
        # 라디오 버튼 생성 (자동으로 리스트의 첫 번째 항목이 기본 선택됨)
        selected_title = st.radio(
            "주차를 선택하세요", 
            options=tab_titles,
            label_visibility="collapsed"
        )

    # 3. 메인 화면 (선택된 탭의 내용 렌더링)
    # 선택된 라디오 버튼의 title과 일치하는 탭 정보를 찾음
    selected_tab = next(t for t in all_tabs if t["display_title"] == selected_title)
    
    # 상단 타이틀
    st.markdown(f"<h2 style='text-align: center; color: #111;'>🎬 {selected_title}</h2>", unsafe_allow_html=True)
    st.write("") # 약간의 여백
    
    # 임베딩 URL 조합
    base_publish_url = st.secrets["PUBLISH_URL_BASE"]
    embed_url = f"{base_publish_url}?gid={selected_tab['gid']}&single=true&widget=false&headers=false&chrome=false"
    
    # 요구사항: 중앙 정렬 & 너비 1200px 고정
    st.markdown(f"""
        <div style="display: flex; justify-content: center; width: 100%;">
            <iframe
                src="{embed_url}"
                style="width: 1200px; height: 1200px; border: 1px solid #e0e0e0; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);"
            ></iframe>
        </div>
    """, unsafe_allow_html=True)

except KeyError as e:
    st.error(f"⚠️ 설정 오류: `.streamlit/secrets.toml` 파일에 {e} 값이 없습니다.")
except Exception as e:
    st.error(f"⚠️ 오류가 발생했습니다: {e}")