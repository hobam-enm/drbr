import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import urllib.parse
import requests

# ===== [ 1. 페이지 기본 설정 및 CSS 스타일링 ] =====
st.set_page_config(
    page_title="드라마 주간 브리핑",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed" # 사이드바 미사용으로 변경
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
    
    /* Selectbox (필터 리스트) 디자인 튜닝 */
    div[data-testid="stSelectbox"] label {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #333333;
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


# ===== [ 3. 가변 너비 계산 (A, B, C열 합산) ] =====
@st.cache_data(ttl=600)
def get_dynamic_width(sheet_id: str, tab_title: str) -> int:
    """
    구글 API를 호출해 해당 탭의 A, B, C열 픽셀 너비를 읽어온 후 합산합니다.
    """
    try:
        client = get_gspread_client()
        creds = client.auth
        
        # 토큰 갱신 보장
        if not creds.valid:
            import google.auth.transport.requests as req
            creds.refresh(req.Request())
            
        encoded_title = urllib.parse.quote(tab_title)
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?ranges={encoded_title}&fields=sheets(data(columnMetadata(pixelSize)))"
        
        headers = {'Authorization': f'Bearer {creds.token}'}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        col_meta = data['sheets'][0]['data'][0].get('columnMetadata', [])
        
        w_a = col_meta[0].get('pixelSize', 100) if len(col_meta) > 0 else 100
        w_b = col_meta[1].get('pixelSize', 100) if len(col_meta) > 1 else 100
        w_c = col_meta[2].get('pixelSize', 100) if len(col_meta) > 2 else 100
        
        # 스크롤 여유분을 위해 20픽셀 정도 추가
        return w_a + w_b + w_c + 20
        
    except Exception as e:
        print(f"너비 계산 오류: {e}")
        return 1200 # API 호출 실패 시 기본 1200px


# ===== [ 4. 메인 앱 실행 로직 ] =====
try:
    # 1. 시크릿에서 SHEET_ID를 가져와 탭 리스트 로드
    sheet_id = st.secrets["SHEET_ID"]
    all_tabs = fetch_all_tabs(sheet_id)
    
    if not all_tabs:
        st.warning("구글 시트에 탭이 없습니다.")
        st.stop()

    # 2. 필터 리스트 (메인 화면 상단)
    tab_titles = [t["display_title"] for t in all_tabs]
    
    # Selectbox를 사용해 필터 형태로 탭 선택 (첫 번째 탭이 기본 선택됨)
    selected_title = st.selectbox(
        "📅 주차 선택", 
        options=tab_titles,
        index=0
    )

    # 3. 메인 화면 (선택된 탭의 내용 렌더링)
    selected_tab = next(t for t in all_tabs if t["display_title"] == selected_title)
    
    # 선택된 탭의 A+B+C열 너비 합산값 가져오기
    dynamic_width = get_dynamic_width(sheet_id, selected_tab['original_title'])
    
    # 상단 타이틀
    st.markdown(f"<h2 style='text-align: center; color: #111;'>🎬 {selected_title}</h2>", unsafe_allow_html=True)
    st.write("") # 약간의 여백
    
    # 임베딩 URL 조합
    base_publish_url = st.secrets["PUBLISH_URL_BASE"]
    embed_url = f"{base_publish_url}?gid={selected_tab['gid']}&single=true&widget=false&headers=false&chrome=false"
    
    # 요구사항: 중앙 정렬 & 가변 너비 적용
    st.markdown(f"""
        <div style="display: flex; justify-content: center; width: 100%;">
            <iframe
                src="{embed_url}"
                style="width: {dynamic_width}px; height: 1200px; border: 1px solid #e0e0e0; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);"
            ></iframe>
        </div>
    """, unsafe_allow_html=True)

except KeyError as e:
    st.error(f"⚠️ 설정 오류: `.streamlit/secrets.toml` 파일에 {e} 값이 없습니다.")
except Exception as e:
    st.error(f"⚠️ 오류가 발생했습니다: {e}")