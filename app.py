import io
import requests
from bs4 import BeautifulSoup
import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="스레드 홍보글 생성기 (Gemini)",
    page_icon="📱",
    layout="centered"
)

# 2. 타이틀 및 설명
st.title("📱 스레드(Threads) 홍보글 자동 생성기")
st.caption("구글 Gemini API를 활용해 제품 링크만으로 제품명과 이미지를 자동 분석하여 스레드 글을 생성합니다.")

# 3. API 키 설정
api_key = st.secrets.get("GEMINI_API_KEY", "")

st.sidebar.header("🔑 API 키 설정")
if not api_key:
    api_key = st.sidebar.text_input(
        "Google Gemini API Key",
        type="password",
        help="Google AI Studio(https://aistudio.google.com/)에서 무료로 발급받을 수 있습니다."
    )
else:
    st.sidebar.success("🔒 Secrets에서 API 키를 로드했습니다.")

# 4. URL 메타데이터(제품명, 이미지) 추출 함수
def extract_meta_from_url(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # 대표 제목 가져오기 (og:title -> title 태그)
    title_tag = soup.find("meta", property="og:title") or soup.find("title")
    title = title_tag["content"] if title_tag and title_tag.get("content") else (title_tag.string if title_tag else "추천 제품")
    
    # 대표 이미지 가져오기 (og:image)
    image_tag = soup.find("meta", property="og:image")
    image_bytes = None
    if image_tag and image_tag.get("content"):
        img_url = image_tag["content"]
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        img_res = requests.get(img_url, headers=headers, timeout=10)
        if img_res.status_code == 200:
            image_bytes = img_res.content

    return title.strip(), image_bytes

# 5. Gemini 생성 함수
def generate_thread_post(api_key: str, product_name: str, image_bytes: bytes = None) -> str:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    safe_product_name = product_name.replace("\n", " ").strip()
    
    prompt = f"""
당신은 스레드(Threads)에서 반응이 좋은 트렌디한 제품 추천 에디터입니다.
제공된 정보 [제품명/페이지 제목: {safe_product_name}] 및 이미지를 바탕으로 스레드 추천 글을 작성하세요.

[작성 규칙]
1. 제품의 시각적 특징이나 주요 매력을 자연스럽게 언급하세요.
2. 지나친 광고 표현은 피하고, 친구에게 솔직히 추천해주는 듯한 친근하고 유쾌한 톤(200~300자 내외)으로 작성하세요.
3. 첫 문장은 유저의 공감이나 호기심을 유발하는 질문이나 후킹 문구로 시작하세요.
4. 핵심 포인트는 이모지와 함께 읽기 편하게 구성하세요.
5. 글 마지막 줄에는 반드시 아래 대가성 문구를 변형 없이 그대로 포함하세요:
   "이 포스팅은 토스쇼핑 쉐어링크 활동의 일환으로, 링크를 통한 구매 시 일정 수수료를 지급받습니다."
"""
    contents = [prompt]
    if image_bytes:
        image = Image.open(io.BytesIO(image_bytes))
        image.thumbnail((1024, 1024))
        contents.append(image)

    response = model.generate_content(contents)
    return response.text

# 6. 메인 입력 폼
st.subheader("🛍️ 제품 링크 입력")
share_link = st.text_input("토스 / 쿠팡 쉐어링크 URL", placeholder="https://...")

# 7. 생성 실행 및 결과 출력
st.markdown("---")
if st.button("✨ 스레드 홍보글 생성하기", use_container_width=True):
    if not api_key:
        st.error("⚠️ Gemini API Key를 입력하거나 Secrets를 확인해주세요.")
    elif not share_link.strip():
        st.warning("⚠️ 홍보할 제품 링크를 입력해주세요.")
    else:
        with st.spinner("링크 분석 및 이미지 추출 중..."):
            try:
                # 1단계: 크롤링으로 정보 추출
                extracted_title, image_bytes = extract_meta_from_url(share_link)
                st.info(f"📌 감지된 제품 정보: **{extracted_title}**")
                
                # 2단계: Gemini AI글 작성
                with st.spinner("AI가 홍보글을 작성 중입니다..."):
                    raw_post = generate_thread_post(api_key, extracted_title, image_bytes)
                    
                    disclosure = "이 포스팅은 토스쇼핑 쉐어링크 활동의 일환으로, 링크를 통한 구매 시 일정 수수료를 지급받습니다."
                    if disclosure in raw_post:
                        final_post = raw_post.replace(disclosure, f"👉 제품 보러가기: {share_link}\n\n{disclosure}")
                    else:
                        final_post = f"{raw_post}\n\n👉 제품 보러가기: {share_link}\n\n{disclosure}"

                    st.success("🎉 스레드 홍보글이 완성되었습니다!")
                    st.code(final_post, language=None)
                    
            except requests.exceptions.RequestException:
                st.error("⚠️ 링크 접속에 실패했습니다. 올바른 URL인지 확인해주세요.")
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "quota" in err_msg.lower():
                    st.error("⚠️ API 무료 분당 호출 제한(Rate Limit)에 도달했습니다. 1분 후 다시 시도해 주세요.")
                else:
                    st.error(f"오류가 발생했습니다: {err_msg}")
