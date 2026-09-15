import hashlib
import io
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
st.caption("구글 Gemini API(무료)를 활용해 제품 사진과 이름만으로 맞춤형 스레드 글을 생성합니다.")

# 3. API 키 설정 (st.secrets 우선, 없으면 사이드바 fallback)
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

st.sidebar.markdown("""
---
### 💡 사용 방법
1. **Gemini API Key**를 입력하거나 Secrets에 설정합니다.
2. **제품명**과 **제품 사진(5MB 이하)**을 업로드합니다.
3. **[홍보글 생성하기]** 버튼을 클릭합니다.
4. 완성된 글을 오른쪽 상단 버튼으로 복사해 스레드에 공유하세요!
""")

# 4. 캐싱 함수 (개선점 1: MD5 해시 기반 Caching 처리)
@st.cache_data(show_spinner=False)
def generate_thread_post(api_key: str, product_name: str, image_hash: str, image_bytes: bytes) -> str:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 이미지 해상도 최적화 (1024x1024)
    image = Image.open(io.BytesIO(image_bytes))
    image.thumbnail((1024, 1024))
    
    # 프롬프트 인젝션 방지
    safe_product_name = product_name.replace("\n", " ").strip()
    
    prompt = f"""
당신은 스레드(Threads)에서 반응이 좋은 트렌디한 제품 추천 에디터입니다.
제공된 [제품 사진]과 [제품명: {safe_product_name}]을(를) 바탕으로 스레드 추천 글을 작성하세요.

[작성 규칙]
1. 이미지를 정밀하게 분석하여 눈에 띄는 디자인, 색감, 재질, 실사용 장면 또는 핵심 특징을 언급하세요.
2. 지나친 광고 표현은 피하고, 친구에게 솔직히 추천해주는 듯한 친근하고 유쾌한 톤(200~300자 내외)으로 작성하세요.
3. 첫 문장은 유저의 공감이나 호기심을 유발하는 질문이나 후킹 문구로 시작하세요.
4. 핵심 포인트는 이모지와 함께 읽기 편하게 구성하세요.
5. 글 마지막 줄에는 반드시 아래 대가성 문구를 변형 없이 그대로 포함하세요:
   "이 포스팅은 토스쇼핑 쉐어링크 활동의 일환으로, 링크를 통한 구매 시 일정 수수료를 지급받습니다."
"""

    response = model.generate_content([prompt, image])
    return response.text

# 5. 메인 입력 폼
st.subheader("🛍️ 제품 정보 입력")

col1, col2 = st.columns([1, 1])

with col1:
    product_name = st.text_input("제품명", placeholder="예: 돈시몬 100% 토마토 주스 1L")
    share_link = st.text_input("토스 쉐어링크 URL (선택)", placeholder="https://toss.im/...")

with col2:
    uploaded_file = st.file_uploader("제품 사진 업로드 (최대 5MB)", type=["jpg", "jpeg", "png", "webp"])

# 개선점 5: 파일 크기 실시간 표시 및 제한 검증
is_image_valid = False
if uploaded_file is not None:
    file_size_mb = uploaded_file.size / (1024 * 1024)
    st.caption(f"📊 업로드된 파일 크기: {file_size_mb:.2f}MB")
    
    MAX_SIZE_MB = 5
    if file_size_mb > MAX_SIZE_MB:
        st.error(f"⚠️ 이미지 용량이 너무 큽니다. {MAX_SIZE_MB}MB 이하의 이미지를 업로드해 주세요.")
    else:
        is_image_valid = True
        image = Image.open(uploaded_file)
        st.image(image, caption="업로드된 제품 이미지", use_container_width=True)

# 6. 생성 실행 및 결과 출력
st.markdown("---")
if st.button("✨ 스레드 홍보글 생성하기", use_container_width=True):
    if not api_key:
        st.error("⚠️ 사이드바 또는 Secrets에 Google Gemini API Key를 설정해주세요.")
    elif not product_name.strip():
        st.warning("⚠️ 제품명을 입력해주세요.")
    elif not is_image_valid:
        st.warning("⚠️ 5MB 이하의 올바른 제품 사진을 업로드해주세요.")
    else:
        with st.spinner("AI가 제품 사진과 디자인을 분석하여 홍보글을 작성 중입니다..."):
            try:
                # MD5 해시 생성 및 생성 함수 호출
                image_bytes = uploaded_file.getvalue()
                image_hash = hashlib.md5(image_bytes).hexdigest()
                
                raw_post = generate_thread_post(api_key, product_name, image_hash, image_bytes)
                
                # 쉐어링크 처리
                disclosure = "이 포스팅은 토스쇼핑 쉐어링크 활동의 일환으로, 링크를 통한 구매 시 일정 수수료를 지급받습니다."
                final_post = raw_post
                if share_link:
                    if disclosure in final_post:
                        final_post = final_post.replace(disclosure, f"👉 제품 보러가기: {share_link}\n\n{disclosure}")
                    else:
                        final_post += f"\n\n👉 제품 보러가기: {share_link}\n\n{disclosure}"

                st.success("🎉 스레드 홍보글이 완성되었습니다!")
                
                # 개선점 3: 글자 수 측정 및 가이드라인 알림
                char_count = len(final_post)
                st.metric(label="생성된 글자 수", value=f"{char_count}자", help="스레드 추천 권장 분량: 200~300자 내외")
                
                if char_count < 200:
                    st.warning("💡 생성된 글이 권장 분량(200~300자)보다 다소 짧습니다. 필요 시 [다시 생성하기]를 눌러보세요.")
                elif char_count > 300:
                    st.info("ℹ️ 생성된 글이 권장 분량(200~300자)보다 깁니다. 핵심 내용만 살짝 줄여서 올리시면 좋습니다.")

                # 개선점 4: 우측 상단 자체 복사 버튼이 내장된 Code 블록 출력
                st.subheader("📝 생성된 게시글")
                st.code(final_post, language=None)
                
            # 개선점 2: Gemini API 전용 트래픽/쿼터 제한 예외 처리
            except genai.types.APIError as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    st.error("⚠️ API 무료 분당 호출 제한(Rate Limit)에 도달했습니다. 1분 후 다시 시도해 주세요.")
                else:
                    st.error(f"Gemini API 오류: {str(e)}")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
