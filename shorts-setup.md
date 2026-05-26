# YouTube Shorts 자동 생성 및 업로드 시스템 설정 가이드

본 시스템은 n8n과 Google Gemini API, Pexels API, 그리고 Synology NAS상의 Python 렌더러를 활용하여 100% 무료로 유튜브 쇼츠(Shorts) 영상을 자동으로 생성하고 업로드할 수 있도록 구성되어 있습니다.

---

## 1. 요구사항 및 API 키 발급

원활한 작동을 위해 총 3가지의 API 설정 및 인증이 필요합니다.

### A. Google Gemini API 키 (대본 생성용 - 무료)
1. [Google AI Studio](https://aistudio.google.com/)에 접속하여 구글 계정으로 로그인합니다.
2. **Get API Key** 버튼을 클릭하여 새로운 API 키를 생성합니다.
3. 생성된 API 키를 복사해 둡니다.

### B. Pexels API 키 (배경 동영상 검색용 - 무료)
1. [Pexels](https://www.pexels.com/api/) 웹사이트에 가입합니다.
2. API 메뉴로 이동하여 **Request API Key**를 진행합니다.
3. 발급받은 API 키를 복사해 둡니다. (무료 계정은 충분한 일일 요청 횟수를 제공합니다.)

### C. YouTube Data API v3 OAuth2 설정 (유튜브 업로드용 - 무료)
유튜브 업로드는 보안 상 OAuth2 방식을 사용해야 합니다.
1. [Google Cloud Console](https://console.cloud.google.com/)에 접속합니다.
2. 새 프로젝트를 생성합니다.
3. **API 및 서비스 > 라이브러리**로 이동하여 **YouTube Data API v3**를 검색하고 활성화합니다.
4. **API 및 서비스 > OAuth 동의 화면**으로 이동합니다.
   - User Type을 **외부(External)**로 선택합니다.
   - 앱 이름, 사용자 지원 이메일 등을 입력합니다.
   - **테스트 사용자(Test Users)** 단계에서 쇼츠를 업로드할 본인의 유튜브 채널 구글 계정을 반드시 추가해 줍니다.
5. **API 및 서비스 > 사용자 인증 정보**로 이동합니다.
   - **사용자 인증 정보 만들기 > OAuth 클라이언트 ID**를 선택합니다.
   - 애플리케이션 유형을 **웹 애플리케이션**으로 지정합니다.
   - **승인된 리디렉션 URI**에 다음 주소를 추가합니다:
     - `https://oauth.n8n.io/oauth2/callback` (n8n 클라우드 혹은 공식 콜백 서버를 이용할 경우)
     - 또는 본인 NAS n8n의 도메인/IP 주소를 포함한 콜백 주소 (예: `http://<NAS_IP>:5678/rest/oauth2-credential/callback`)
6. 생성된 **클라이언트 ID(Client ID)**와 **클라이언트 보안 비밀번호(Client Secret)**를 복사해 둡니다.

---

## 2. n8n 환경 변수 및 크레덴셜 설정

n8n 컨테이너가 API 키들을 안전하게 사용할 수 있도록 NAS 호스트 환경에서 환경 변수를 주입하거나 n8n 내부에서 설정합니다.

### A. NAS n8n 컨테이너 환경 변수 추가
NAS에서 n8n 컨테이너를 구동할 때 아래 환경 변수를 컨테이너 설정이나 `docker-compose.yml`의 `environment` 섹션에 추가해 줍니다:
- `GEMINI_API_KEY`: Google AI Studio에서 발급받은 API 키
- `PEXELS_API_KEY`: Pexels에서 발급받은 API 키

### B. YouTube OAuth2 Credential 등록
1. n8n 웹 대시보드(`http://<NAS_IP>:5678`)에 접속합니다.
2. **Credentials > Add Credential**을 클릭합니다.
3. **YouTube OAuth2 API**를 검색하여 선택합니다.
4. Google Cloud Console에서 발급받은 **Client ID**와 **Client Secret**을 입력합니다.
5. **Sign in with Google**을 클릭하여 테스트 사용자로 등록된 유튜브 계정으로 로그인하고 권한을 승인합니다.

---

## 3. 워크플로우 가져오기 및 테스트

1. 본 저장소에 포함된 `workflow_shorts.json` 파일의 내용을 전체 복사합니다.
2. n8n 대시보드에서 **Workflows > New Workflow**를 만듭니다.
3. 빈 화면에서 `Ctrl + V`를 누르거나 우측 상단 메뉴에서 **Import from File**을 클릭하여 복사한 내용을 붙여넣습니다.
4. 워크플로우가 불러와지면 각 노드의 연결을 확인합니다.
5. **Webhook Trigger** 노드 또는 수동 실행을 통해 아래 형식의 JSON 데이터를 전송하여 첫 쇼츠 비디오 생성을 테스트합니다:

```json
{
  "news_content": "여기에 요약하고자 하는 뉴스 기사 원문이나 텍스트를 입력하세요. Gemini가 자동으로 이를 바탕으로 45초 분량의 매끄러운 숏츠 대본을 작성하고, 어울리는 키워드를 추출하여 배경 영상을 매칭해 비디오를 생성합니다."
}
```

---

## 4. 문제 해결 (Troubleshooting)

### Q. 자막의 한글이 깨지거나 사각형(ㅁ)으로 나옵니다.
* **원인:** Docker 이미지 내에 한글 폰트가 설치되어 있지 않거나 경로 매칭이 실패한 경우입니다.
* **해결책:** 본 패키지는 빌드 시 데비안의 `fonts-nanum`을 포함하도록 Dockerfile이 설정되어 있습니다. 이미지가 최신 버전으로 올바르게 빌드되었는지 `docker build` 로그를 확인해 주십시오.

### Q. 비디오 생성 속도가 너무 느립니다.
* **원인:** CPU만을 사용하는 NAS 환경 특성상 영상 디코딩/인코딩 처리에 시간이 다소 걸립니다. (보통 45초 영상 렌더링에 약 2~5분 소요)
* **해결책:** 렌더링 노드가 타임아웃되지 않도록 n8n의 `Execute Command` 노드 타임아웃 제한이 기본값보다 넉넉한지 확인하십시오. (필요 시 타임아웃을 600초 이상으로 설정)
