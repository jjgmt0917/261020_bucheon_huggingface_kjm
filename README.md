# 손글씨 인식기 (261020_bucheon_huggingface_kjm)

손글씨 사진을 올리면 Hugging Face 비전 모델(Inference Providers)이 글자로 바꿔주고,
확인·수정한 뒤 txt 파일로 저장하는 Streamlit 웹앱입니다.

- 모델을 내려받지 않고 API로 호출합니다 (`huggingface_hub.InferenceClient`)
- **Python 3.8 이상**에서 동작합니다
- 한글·영어 손글씨를 모두 읽습니다 (언어는 모델이 알아서 구분)

## 구조
```
README.md
.gitignore
261020_bucheon_hugging_kjm/
├── app.py                  Streamlit 앱 (업로드 → 인식 → 수정 → 재판독/저장)
├── requirements.txt        필요 라이브러리
├── .env.example            환경변수 예시
├── .streamlit/config.toml  Streamlit 설정
├── samples/test_font.png   테스트용 이미지 (폰트로 만든 글씨)
└── saved/                  저장한 txt 파일 (자동 생성, git 제외)
```

## 사용법
1. 레포를 받고 **작업 폴더로 이동**한 뒤 가상환경 및 설치
   ```bash
   git clone https://github.com/jjgmt0917/261020_bucheon_huggingface_kjm.git
   cd 261020_bucheon_huggingface_kjm/261020_bucheon_hugging_kjm
   python -m venv venv
   venv\Scriptsctivate          # macOS/Linux: source venv/bin/activate
   pip install -r requirements.txt
   ```
2. `.env.example` 을 복사해 `.env` 생성 후 토큰 입력 (**필수**)
   ```
   HF_TOKEN=...      # https://huggingface.co/settings/tokens
   ```
   `.env` 는 작업 폴더 → 상위 폴더 순서로 찾습니다.
3. 실행
   ```bash
   streamlit run app.py
   ```
   (처음 실행하면 이메일을 묻는데, 그냥 Enter 를 누르면 됩니다)
4. 브라우저에서 http://localhost:8501 접속

## 사용 흐름
1. **손글씨 사진 업로드** → 자동으로 글자 인식
2. 결과 상자에서 확인 — 틀린 글자는 **직접 수정** 가능
3. 결과가 이상하면 **🔄 재판독** — 다른 모델로 다시 읽습니다
4. 맞으면 **💾 저장** → `saved/ocr_날짜_시간.txt` 로 저장되고 다운로드 버튼도 나옵니다

## 사용 모델
재판독을 누를 때마다 아래 순서로 넘어갑니다. 오류가 나는 모델은 건너뜁니다.

| 순서 | 모델 |
|---|---|
| 1 | `google/gemma-4-31B-it` |
| 2 | `Qwen/Qwen3-VL-8B-Instruct` |
| 3 | `Qwen/Qwen2.5-VL-7B-Instruct` |
| 4 | `google/gemma-4-26B-A4B-it` |

## 참고 / 한계
- 모델마다 결과가 조금씩 달라서, 같은 사진도 재판독하면 다르게 나올 수 있습니다. 끝까지 틀리면 직접 수정하세요.
- 기울거나 모눈종이 위에 쓴 사진도 읽지만, 글씨가 작거나 흐리면 틀릴 수 있습니다.
- 무료 사용량이 모두 소진되면 `모든 모델이 응답하지 않았어요` 라고 표시됩니다. 토큰과 사용량을 확인하세요.
- 사진은 선택한 Hugging Face provider 로 전송됩니다. 개인정보가 담긴 사진은 올리지 마세요.

## 주의
- `.env` 는 `.gitignore` 로 제외되어 있습니다. 토큰을 절대 커밋하지 마세요.
