import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# ===== [ 1. 페이지 기본 설정 및 CSS 스타일링 ] =====
# 앱의 기본 레이아웃을 설정하고, 메인 리스트의 심미성을 높이기 위한 CSS를 주입합니다.
st.set_page_config(
    page_title="드라마 주간 브리핑",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* 상단 헤더 숨김 처리 (앱 느낌 강조) */
    header[data-testid="stHeader"] { display: none !important; }
    
    /* 메인 타이틀 스타일 */
    .main-title {
        font-size: 36px;
        font-weight: 800;
        text-align: center;
        margin-top: 2rem;
        margin-bottom: 3rem;
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* 리스트 카드(버튼) 스타일링 */
    div.stButton > button {
        background-color: #ffffff;
        border: 1px solid #e0e5ec;
        border-radius: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        height: 120px;
        width: 100%;
        font-size: 20px;
        font-weight: 700;
        color: #333333;
        transition: all 0.3s ease;
    }
    
    /* 카드 호버(마우스 오버) 액션 */
    div.stButton > button:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        border-color: #4b6cb7;
        color: #4b6cb7;
    }
    
    /* 뒤로가기 버튼용 특별 스타일 */
    div[data-testid="stHorizontalBlock"] div.stButton > button {
        height: auto;
        font-size: 16px;
        padding: 8px 24px;
        background-color: #f1f3f5;
        border: none;
        box-shadow: none;
    }
    div[data-testid="stHorizontalBlock"] div.stButton > button:hover {
        background-color: #e9ecef;
        transform: none;
    }
</style>
""", unsafe_allow_html=True)


# ===== [ 2. 세션 상태 초기화 ] =====
# 사용자가 선택한 주차(탭)의 정보를 저장하여 화면 전환을 제어합니다.
if "selected_title" not in st.session_state:
    st.session_state.selected_title = None

if "selected_gid" not in st.session_state:
    st.session_state.selected_gid = None


# ===== [ 3. 데이터 로드 (구글 시트 연동) ] =====
# gspread를 이용해 구글 시트의 모든 탭 정보를 동적으로 가져옵니다.

@st.cache_resource(ttl=600)
def get_gspread_client():
    """
    st.secrets에 저장된 GCP 서비스 계정 정보로 gspread 클라이언트를 인증합니다.
    """
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def fetch_all_tabs(sheet_id: str):
    """
    주어진 스프레드시트 ID에서 모든 탭(Worksheet)의 이름과 GID를 리스트로 반환합니다.
    가장 최근에 만든 탭이 앞에 오도록 역순으로 뒤집어서 반환합니다.
    """
    client = get_gspread_client()
    spreadsheet = client.open_by_key(sheet_id)
    
    worksheets = spreadsheet.worksheets()
    
    tab_list = []
    for ws in worksheets:
        tab_list.append({
            "title": ws.title,
            "gid": ws.id
        })
        
    # 최신 주차가 위로 오도록 리스트 역순 정렬 (필요시 제거 가능)
    return tab_list[::-1]


# ===== [ 4. 화면 렌더링 함수 ] =====
# 메인 리스트 화면과 상세 브리핑 화면을 분리하여 렌더링합니다.

def render_main_list(tabs):
    """
    모든 주차별 탭 정보를 바탕으로 그리드 형태의 카드 리스트를 생성합니다.
    """
    st.markdown('<div class="main-title">🎬 드라마 주간 브리핑</div>', unsafe_allow_html=True)
    
    # 3열 그리드로 카드 배치
    cols_per_row = 3
    
    for i in range(0, len(tabs), cols_per_row):
        row_tabs = tabs[i:i + cols_per_row]
        cols = st.columns(cols_per_row)
        
        for col, tab in zip(cols, row_tabs):
            with col:
                # 버튼 클릭 시 해당 탭의 정보를 세션에 저장하고 새로고침
                if st.button(f"🗓️ {tab['title']}", key=f"btn_{tab['gid']}"):
                    st.session_state.selected_title = tab['title']
                    st.session_state.selected_gid = tab['gid']
                    st.rerun()


def render_detail_view(title, gid):
    """
    선택된 주차의 구글 시트 웹 게시 URL을 iframe으로 임베딩하여 보여줍니다.
    """
    # 상단 네비게이션 영역 (뒤로 가기 버튼 및 타이틀)
    col1, col2 = st.columns([1, 8])
    
    with col1:
        if st.button("⬅️ 목록으로"):
            st.session_state.selected_title = None
            st.session_state.selected_gid = None
            st.rerun()
            
    with col2:
        st.markdown(f"### {title}")
    
    st.divider()
    
    # 임베딩 URL 조합 (st.secrets에서 기본 웹 게시 URL을 가져옵니다)
    # publish_url 예시: "https://docs.google.com/spreadsheets/d/e/2PACX-.../pubhtml"
    base_publish_url = st.secrets["PUBLISH_URL_BASE"]
    
    # iframe 최적화를 위한 파라미터 추가 (헤더, 눈금선 등 숨김)
    embed_url = f"{base_publish_url}?gid={gid}&single=true&widget=false&headers=false&chrome=false"
    
    # iframe 렌더링 (높이는 자유롭게 스크롤 되도록 넉넉하게 설정)
    st.markdown(f"""
        <iframe
            src="{embed_url}"
            style="width: 100%; height: 1200px; border: none; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);"
        ></iframe>
    """, unsafe_allow_html=True)


# ===== [ 5. 메인 앱 실행 로직 ] =====
try:
    # 1. 시크릿에서 SHEET_ID를 가져와 탭 리스트 로드
    sheet_id = st.secrets["SHEET_ID"]
    all_tabs = fetch_all_tabs(sheet_id)
    
    # 2. 세션 상태에 따라 화면 분기
    if st.session_state.selected_gid is None:
        render_main_list(all_tabs)
    else:
        render_detail_view(st.session_state.selected_title, st.session_state.selected_gid)

except KeyError as e:
    st.error(f"⚠️ 설정 오류: `.streamlit/secrets.toml` 파일에 {e} 값이 없습니다.")
except Exception as e:
    st.error(f"⚠️ 오류가 발생했습니다: {e}")