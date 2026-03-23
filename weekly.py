import urllib.parse
import requests
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# [수정된 부분] 토큰 갱신을 위해 반드시 필요한 모듈 추가
from google.auth.transport.requests import Request 


# ===== [ 1. 페이지 기본 설정 및 CSS 스타일링 ] =====
st.set_page_config(
    page_title="드라마 주간 브리핑",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
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
    
    /* Selectbox 디자인 튜닝 */
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
    
    worksheets = spreadsheet.worksheets()
    
    tab_list = []
    for ws in worksheets:
        tab_list.append({
            "original_title": ws.title,
            "display_title": f"{ws.title} 드라마 브리핑", 
            "gid": ws.id
        })
        
    return tab_list


# ===== [ 3. 가변 너비 계산 (A, B, C열 합산) ] =====
# 탭 이름마다 너비가 다를 수 있으므로 탭 이름을 기준으로 캐싱합니다.
@st.cache_data(ttl=600)
def get_dynamic_width(sheet_id: str, tab_title: str) -> int:
    try:
        client = get_gspread_client()
        creds = client.auth
        
        # [수정된 부분] 토큰이 만료되었을 경우 Request()를 통해 갱신
        if not creds.valid:
            creds.refresh(Request())
            
        # [수정된 부분] 탭 이름에 띄어쓰기가 있을 경우를 대비해 작은따옴표로 감싸기
        encoded_title = urllib.parse.quote(f"'{tab_title}'")
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?ranges={encoded_title}&fields=sheets(data(columnMetadata(pixelSize)))"
        
        headers = {'Authorization': f'Bearer {creds.token}'}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # API에서 넘어온 열(Column) 사이즈 메타데이터 추출
        col_meta = data.get('sheets', [{}])[0].get('data', [{}])[0].get('columnMetadata', [])
        
        # A, B, C열의 픽셀 사이즈 (데이터가 없으면 기본값 100 적용)
        w_a = col_meta[0].get('pixelSize', 100) if len(col_meta) > 0 else 100
        w_b = col_meta[1].get('pixelSize', 100) if len(col_meta) > 1 else 100
        w_c = col_meta[2].get('pixelSize', 100) if len(col_meta) > 2 else 100
        
        # 합산 + 스크롤 여유분 40px
        calculated_width = w_a + w_b + w_c + 40
        return calculated_width
        
    except Exception as e:
        # 에러 발생 시 우측 하단에 알림을 띄워 원인 파악 가능하게 조치
        st.toast(f"⚠️ 너비 계산 실패 (기본값 적용됨): {e}")
        return 1200


# ===== [ 4. 메인 앱 실행 로직 ] =====
try:
    sheet_id = st.secrets["SHEET_ID"]
    all_tabs = fetch_all_tabs(sheet_id)
    
    if not all_tabs:
        st.warning("구글 시트에 탭이 없습니다.")
        st.stop()

    tab_titles = [t["display_title"] for t in all_tabs]
    
    # 상단 Selectbox (필터 리스트)
    selected_title = st.selectbox(
        "📅 주차 선택", 
        options=tab_titles,
        index=0
    )

    selected_tab = next(t for t in all_tabs if t["display_title"] == selected_title)
    
    # 동적 너비 계산 함수 호출
    dynamic_width = get_dynamic_width(sheet_id, selected_tab['original_title'])
    
    st.markdown(f"<h2 style='text-align: center; color: #111;'>🎬 {selected_title}</h2>", unsafe_allow_html=True)
    st.write("") 
    
    base_publish_url = st.secrets["PUBLISH_URL_BASE"]
    embed_url = f"{base_publish_url}?gid={selected_tab['gid']}&single=true&widget=false&headers=false&chrome=false"
    
    # [수정된 부분] iframe id를 동적으로 부여해 탭 변경 시 스트림릿이 즉시 재렌더링하도록 강제함
    st.markdown(f"""
        <div style="display: flex; justify-content: center; width: 100%;">
            <iframe
                id="iframe-{selected_tab['gid']}"
                src="{embed_url}"
                style="width: {dynamic_width}px; height: 1200px; border: 1px solid #e0e0e0; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transition: width 0.3s ease;"
            ></iframe>
        </div>
    """, unsafe_allow_html=True)

except KeyError as e:
    st.error(f"⚠️ 설정 오류: `.streamlit/secrets.toml` 파일에 {e} 값이 없습니다.")
except Exception as e:
    st.error(f"⚠️ 오류가 발생했습니다: {e}")