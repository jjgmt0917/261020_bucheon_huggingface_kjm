import base64
import io
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from PIL import Image, ImageOps

# 1. 환경 변수 불러오기 (.env: 이 폴더 우선, 없으면 상위 폴더들)
BASE_DIR = Path(__file__).parent
for folder in (BASE_DIR, BASE_DIR.parent, BASE_DIR.parent.parent):
    load_dotenv(folder / ".env")
HF_TOKEN = os.getenv("HF_TOKEN")

SAVE_DIR = BASE_DIR / "saved"
MAX_SIDE = 1600  # 업로드 이미지는 이 크기로 줄여서 보낸다

LANGS = ["한글", "영어", "한글 + 영어"]

# 재판독할 때마다 다음 모델로 넘어간다 (같은 모델은 같은 사진을 같게 읽는 경우가 많기 때문)
MODELS = [
    ("google/gemma-4-31B-it", "Gemma 4 31B"),
    ("Qwen/Qwen3-VL-8B-Instruct", "Qwen3-VL 8B"),
    ("Qwen/Qwen2.5-VL-7B-Instruct", "Qwen2.5-VL 7B"),
    ("google/gemma-4-26B-A4B-it", "Gemma 4 26B"),
]

PROMPTS = {
    "한글": "이 이미지의 손글씨 중 한글(숫자 포함)만 옮겨 적어줘. 영어 알파벳으로 쓴 글씨는 모두 건너뛰어.",
    "영어": "이 이미지의 손글씨 중 영어 알파벳(숫자 포함)만 옮겨 적어줘. 한글로 쓴 글씨는 모두 건너뛰어.",
    "한글 + 영어": "이 이미지에 손으로 쓴 글씨(한글, 영어)를 쓰인 그대로 옮겨 적어줘.",
}
RULES = " 줄바꿈은 원본 그대로 두고, 글씨만 적어. 설명, 따옴표, 번역은 절대 붙이지 마. 글씨가 없으면 빈 칸으로 둬."

client = InferenceClient(api_key=HF_TOKEN) if HF_TOKEN else None


def to_data_url(data):
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def ask(model, data_url, lang):
    res = client.chat.completions.create(
        model=model,
        max_tokens=500,
        temperature=0,
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": data_url}},
            {"type": "text", "text": PROMPTS[lang] + RULES},
        ]}],
    )
    text = (res.choices[0].message.content or "").strip()
    return text.strip("`").strip()


def run_ocr(start):
    """start 번째 모델부터 시도하고, 오류가 나면 다음 모델로 넘어간다."""
    s = st.session_state
    s.error = None
    data_url = to_data_url(s.image_bytes)
    failed = []
    for step in range(len(MODELS)):
        idx = (start + step) % len(MODELS)
        model, label = MODELS[idx]
        try:
            text = ask(model, data_url, s.lang)
        except Exception as e:
            failed.append(f"{label}: {str(e).splitlines()[0][:120]}")
            continue
        s.model_idx = idx
        s.history.append(text)
        s.text = text
        s.attempts += 1
        if failed:
            s.error = "일부 모델이 응답하지 않아 건너뛰었어요 → " + " / ".join(failed)
        return
    s.error = "모든 모델이 응답하지 않았어요. 토큰이나 사용 한도를 확인해주세요 → " + " / ".join(failed)


def on_upload():
    s = st.session_state
    s.history = []
    s.attempts = 0
    s.saved_path = None
    s.error = None
    f = s.uploader
    if f is None:
        s.image_bytes = None
        s.text = ""
        return
    s.image_bytes = f.getvalue()
    with st.spinner("손글씨 읽는 중..."):
        run_ocr(0)


def on_retry():
    with st.spinner("다른 모델로 다시 읽는 중..."):
        run_ocr((st.session_state.model_idx + 1) % len(MODELS))


def on_lang_change():
    # 언어를 바꾸면 처음 모델부터 다시 읽는다
    s = st.session_state
    if s.get("image_bytes"):
        s.history = []
        with st.spinner("손글씨 읽는 중..."):
            run_ocr(0)


def on_save():
    SAVE_DIR.mkdir(exist_ok=True)
    path = SAVE_DIR / f"ocr_{datetime.now():%Y%m%d_%H%M%S}.txt"
    path.write_text(st.session_state.text, encoding="utf-8")
    st.session_state.saved_path = path


st.set_page_config(page_title="손글씨 인식기", page_icon="✍️")
for key, default in (("image_bytes", None), ("text", ""), ("history", []), ("attempts", 0),
                     ("model_idx", 0), ("saved_path", None), ("error", None)):
    st.session_state.setdefault(key, default)

st.title("✍️ 손글씨 인식기")
st.caption("Hugging Face 비전 모델이 손글씨 사진을 글자로 바꿔요 · 확인·수정 후 txt로 저장")

if not HF_TOKEN:
    st.error("HF_TOKEN 이 없어요. `.env` 파일에 `HF_TOKEN=...` 을 넣고 다시 실행해주세요. (README 참고)")
    st.stop()

st.radio("언어", LANGS, index=2, horizontal=True, key="lang", on_change=on_lang_change)
st.file_uploader("손글씨 사진", type=["png", "jpg", "jpeg", "webp"], key="uploader", on_change=on_upload)

if st.session_state.image_bytes:
    st.image(st.session_state.image_bytes, use_container_width=True)

    st.subheader("인식 결과")
    st.caption(f"모델: {MODELS[st.session_state.model_idx][1]} · 시도 {st.session_state.attempts}회 · 틀린 글자는 직접 고칠 수 있어요")
    if st.session_state.error:
        st.warning(st.session_state.error)
    st.text_area("결과", key="text", height=180, label_visibility="collapsed")

    # 재판독해도 이전과 같은 결과면 안내
    h = st.session_state.history
    if len(h) >= 2 and h[-1] == h[-2]:
        st.info("이전 모델과 같은 결과예요. 위 결과 상자에서 직접 수정해주세요.")

    c1, c2 = st.columns(2)
    c1.button("🔄 재판독 (다른 모델로)", on_click=on_retry, use_container_width=True)
    c2.button("💾 저장", on_click=on_save, type="primary", use_container_width=True,
              disabled=not st.session_state.text.strip())

    if st.session_state.saved_path:
        st.success(f"저장했어요: {st.session_state.saved_path.relative_to(BASE_DIR)}")
        st.download_button("⬇️ txt 다운로드", st.session_state.text,
                           file_name=st.session_state.saved_path.name, mime="text/plain")
else:
    st.info("손글씨 사진을 올려주세요. 글씨가 크고 또렷하게 나올수록 잘 읽어요.")
