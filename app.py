import io
import os
import re
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from huggingface_hub import snapshot_download
from kohandocr.reader import Reader
from PIL import Image, ImageFilter, ImageOps

# 1. 환경 변수 불러오기 (.env: 이 폴더 우선, 없으면 상위 폴더)
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR.parent.parent / ".env")  # 선택: HF_TOKEN (다운로드 속도 제한 완화용)

MODEL_ID = "localdeel/ko-hand-ocr"
SAVE_DIR = BASE_DIR / "saved"

LANGS = ["한글", "영어", "한글 + 영어"]

# 재판독할 때마다 다음 전처리로 넘어간다 (같은 이미지를 같은 방식으로 읽으면 같은 결과가 나오기 때문)
PREPROCESS = ["기본 (원본 그대로)", "대비 높이기 + 선명하게", "흑백 이진화", "이미지 전체를 한 줄로 읽기"]


@st.cache_resource(show_spinner="모델 불러오는 중... (처음에는 다운로드로 시간이 걸려요)")
def load_reader():
    folder = snapshot_download(MODEL_ID, ignore_patterns=["ensemble/*", "assets/*"])
    return Reader(folder, device="cpu")


def to_png(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def binarize(gray):
    # 평균 밝기를 기준으로 글씨/종이를 가른다
    hist = gray.histogram()
    total = sum(hist)
    cut = sum(i * n for i, n in enumerate(hist)) / total * 0.85
    return gray.point(lambda p: 255 if p > cut else 0)


def ocr(reader, data, mode):
    """mode 번째 전처리를 적용해 읽고 줄 목록을 돌려준다."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("L")
    if mode == 3:
        return reader.read([img])
    if mode == 1:
        img = ImageOps.autocontrast(img, cutoff=2).filter(ImageFilter.SHARPEN)
    elif mode == 2:
        img = binarize(ImageOps.autocontrast(img, cutoff=2))
    try:
        lines = [ln for ln in reader.read_photo(to_png(img)) if ln]
    except Exception:
        lines = []
    # 줄을 하나도 못 찾으면 이미지 전체를 한 줄로 읽는다
    return lines or reader.read([img])


def apply_language(lines, lang):
    """선택한 언어에 없는 글자는 결과에서 걸러낸다."""
    if lang == "한글":
        pattern = r"[A-Za-z]"
    elif lang == "영어":
        pattern = r"[ㄱ-ㅎㅏ-ㅣ가-힣]"
    else:
        return [ln for ln in lines if ln.strip()]
    cleaned = [re.sub(r"\s{2,}", " ", re.sub(pattern, "", ln)).strip() for ln in lines]
    return [ln for ln in cleaned if ln]


def run_ocr(mode):
    s = st.session_state
    lines = ocr(load_reader(), s.image_bytes, mode)
    text = "\n".join(apply_language(lines, s.lang))
    s.mode = mode
    s.history.append(text)
    s.text = text
    s.attempts = s.get("attempts", 0) + 1


def on_upload():
    f = st.session_state.uploader
    st.session_state.history = []
    st.session_state.attempts = 0
    st.session_state.saved_path = None
    if f is None:
        st.session_state.image_bytes = None
        st.session_state.text = ""
        return
    st.session_state.image_bytes = f.getvalue()
    run_ocr(0)


def on_retry():
    run_ocr((st.session_state.mode + 1) % len(PREPROCESS))


def on_lang_change():
    # 언어를 바꾸면 처음 전처리로 다시 읽는다
    if st.session_state.get("image_bytes"):
        st.session_state.history = []
        run_ocr(0)


def on_save():
    SAVE_DIR.mkdir(exist_ok=True)
    path = SAVE_DIR / f"ocr_{datetime.now():%Y%m%d_%H%M%S}.txt"
    path.write_text(st.session_state.text, encoding="utf-8")
    st.session_state.saved_path = path


st.set_page_config(page_title="손글씨 인식기", page_icon="✍️")
st.session_state.setdefault("image_bytes", None)
st.session_state.setdefault("text", "")
st.session_state.setdefault("history", [])
st.session_state.setdefault("mode", 0)
st.session_state.setdefault("saved_path", None)

st.title("✍️ 손글씨 인식기")
st.caption(f"Hugging Face `{MODEL_ID}` · 손글씨 사진을 올리면 글자로 바꿔 txt로 저장해요")

st.radio("언어", LANGS, index=2, horizontal=True, key="lang", on_change=on_lang_change)
st.file_uploader("손글씨 사진", type=["png", "jpg", "jpeg", "webp"], key="uploader", on_change=on_upload)

if st.session_state.image_bytes:
    st.image(st.session_state.image_bytes, width="stretch")

    st.subheader("인식 결과")
    st.caption(f"전처리: {PREPROCESS[st.session_state.mode]} · 시도 {st.session_state.attempts}회 · 틀린 글자는 직접 고칠 수 있어요")
    st.text_area("결과", key="text", height=180, label_visibility="collapsed")

    # 재판독해도 이전과 같은 결과면 안내
    h = st.session_state.history
    if len(h) >= 2 and h[-1] == h[-2]:
        st.info("이전과 같은 결과예요. 위 결과 상자에서 직접 수정해주세요.")
    elif st.session_state.attempts >= len(PREPROCESS) and len(set(h)) == 1:
        st.info("모든 전처리에서 같은 결과예요. 직접 수정해주세요.")

    c1, c2 = st.columns(2)
    c1.button("🔄 재판독 (전처리 바꿔서)", on_click=on_retry, width="stretch")
    c2.button("💾 저장", on_click=on_save, type="primary", width="stretch",
              disabled=not st.session_state.text.strip())

    if st.session_state.saved_path:
        st.success(f"저장했어요: {st.session_state.saved_path.relative_to(BASE_DIR)}")
        st.download_button("⬇️ txt 다운로드", st.session_state.text, file_name=st.session_state.saved_path.name,
                           mime="text/plain")
else:
    st.info("손글씨 사진을 올려주세요. 한 줄씩 또렷하게 찍을수록 잘 읽어요.")
