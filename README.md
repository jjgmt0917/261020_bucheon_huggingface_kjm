# 손글씨 인식기 (261020_bucheon_huggingface_kjm)

Hugging Face [`localdeel/ko-hand-ocr`](https://huggingface.co/localdeel/ko-hand-ocr) 모델로
한글·영어 손글씨 사진을 글자로 바꾸고, 확인·수정 후 txt 파일로 저장하는 Streamlit 웹앱입니다.

## 구조
```
app.py                  Streamlit 앱 (업로드 → 인식 → 수정 → 재판독/저장)
requirements.txt        필요 라이브러리
.env.example            환경변수 예시
saved/                  저장한 txt 파일 (자동 생성, git 제외)
```

## 사용법
1. 가상환경 및 설치 (**Python 3.10 이상** 필요 — `ko-hand-ocr` 패키지 요구사항)
   ```bash
   python -m venv venv
   venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
   pip install -r requirements.txt
   ```
2. (선택) `.env.example` 을 복사해 `.env` 생성 후 토큰 입력
   ```
   HF_TOKEN=...      # https://huggingface.co/settings/tokens
   ```
   모델은 공개 모델이라 토큰 없이도 받아집니다. 토큰은 다운로드 속도 제한을 피하는 용도입니다.
   `.env` 는 이 폴더 → 상위 폴더 순서로 찾습니다.
3. 실행
   ```bash
   streamlit run app.py
   ```
4. 브라우저에서 http://localhost:8501 접속 (처음 실행 때 모델(약 78MB)을 자동으로 받습니다)

## 사용 흐름
1. **언어 선택**: 한글 / 영어 / 한글 + 영어
2. **손글씨 사진 업로드** → 자동으로 글자 인식
3. 결과 상자에서 확인 — 틀린 글자는 **직접 수정** 가능
4. 결과가 이상하면 **🔄 재판독** — 전처리 방식을 바꿔 다시 읽습니다
   (기본 → 대비 높이기 → 흑백 이진화 → 이미지 전체를 한 줄로 읽기 순서로 순환)
5. 맞으면 **💾 저장** → `saved/ocr_날짜_시간.txt` 로 저장되고 다운로드 버튼도 나옵니다

## 참고 / 한계
- 이 모델은 **한 줄짜리 손글씨**를 읽도록 만들어졌습니다. 여러 줄 사진은 줄을 자동으로 나눠 읽지만, 한 줄씩 또렷하게 찍을수록 정확합니다.
- 재판독은 같은 이미지에 다른 전처리를 적용하는 방식입니다. 모델은 같은 입력에 항상 같은 결과를 내기 때문에, 전처리로도 안 바뀌면 직접 수정하는 것이 가장 빠릅니다.
- 언어 선택은 결과에서 **선택하지 않은 언어의 글자를 걸러내는** 기능입니다(예: "한글" 선택 시 영문자 제거). 한글과 영어가 섞인 글씨는 인식률이 떨어질 수 있습니다.
- CPU로 동작합니다 (모델이 41M 파라미터라 GPU 없이도 한 줄에 1초 안팎).

## 주의
- `.env` 는 `.gitignore` 로 제외되어 있습니다. 토큰을 절대 커밋하지 마세요.
