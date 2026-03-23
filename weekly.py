import urllib.parse
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

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


# ===== [ 3. 메인 앱 실행 로직 ] =====
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

    # ===== [ 3-1. 특정 탭 기준 가변 너비 계산 로직 ] =====
    # '▶▶25년' 탭의 인덱스를 찾습니다. (왼쪽부터 0번 인덱스 시작)
    divider_index = -1
    for i, t in enumerate(all_tabs):
        if t["original_title"] == "▶▶25년":
            divider_index = i
            break

    # 현재 선택된 탭의 인덱스와 객체를 찾습니다.
    selected_index = -1
    selected_tab = None
    for i, t in enumerate(all_tabs):
        if t["display_title"] == selected_title:
            selected_tab = t
            selected_index = i
            break
    
    # 선택된 탭이 '▶▶25년' 탭보다 뒤(오른쪽)에 있으면 1547px (250+1000+297)
    # 그 앞이거나 '▶▶25년' 탭 자체라면 1200px 적용
    if divider_index != -1 and selected_index > divider_index:
        dynamic_width = 1547
    else:
        dynamic_width = 1200

    
    st.markdown(f"<h2 style='text-align: center; color: #111;'>🎬 {selected_title}</h2>", unsafe_allow_html=True)
    st.write("") 
    
    base_publish_url = st.secrets["PUBLISH_URL_BASE"]
    embed_url = f"{base_publish_url}?gid={selected_tab['gid']}&single=true&widget=false&headers=false&chrome=false"
    
    # iframe id를 동적으로 부여해 탭 변경 시 스트림릿이 즉시 재렌더링하도록 강제함
    st.markdown(f"""
        <div style="display: flex; justify-content: center; width: 100%;">
            <iframe
                id="iframe-{selected_tab['gid']}"
                src="{embed_url}"
                style="width: {dynamic_width}px; height: 4500px; border: 1px solid #e0e0e0; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transition: width 0.3s ease;"
            ></iframe>
        </div>
    """, unsafe_allow_html=True)

except KeyError as e:
    st.error(f"⚠️ 설정 오류: `.streamlit/secrets.toml` 파일에 {e} 값이 없습니다.")
except Exception as e:
    st.error(f"⚠️ 오류가 발생했습니다: {e}")