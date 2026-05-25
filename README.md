# NAS n8n Automation Setup

이 프로젝트는 NAS에 n8n을 Docker로 설치하고, 구글 뉴스 RSS를 크롤링하여 카카오톡(또는 텔레그램/디코드)으로 전송하는 자동화 구축용 공간입니다.

## 진행 절차

1. **NAS 터미널(SSH) 활성화**
   - Synology NAS: `제어판` -> `터미널 및 SNMP` -> `SSH 서비스 활성화` 체크 (포트: 22 또는 사용자 지정)
   - QNAP NAS: `제어판` -> `네트워크 및 파일 서비스` -> `Telnet/SSH` -> `SSH 연결 허용` 체크

2. **n8n Docker Compose 배포**
   - NAS에 SSH로 접속하여 n8n 컨테이너를 구동합니다.
   - 혹은 Synology Container Manager(Docker) UI에서 직접 프로젝트를 생성할 수 있습니다.

3. **n8n 워크플로우 구성**
   - 구글 뉴스 RSS 파싱 및 카카오톡 전송 워크플로우를 가져옵니다.
