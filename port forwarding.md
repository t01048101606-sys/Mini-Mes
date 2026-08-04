# 포트포워딩 설정 가이드 (WSL + Streamlit)

WSL(Ubuntu) 안에서 실행 중인 Streamlit 앱을, 같은 네트워크(Wi-Fi/유선)에 있는
다른 컴퓨터나 휴대폰에서 접속할 수 있게 만드는 절차입니다.

WSL2는 기본적으로 Windows 뒤에 NAT로 숨어있어서, `0.0.0.0`으로 띄워도
WSL 안에서만 열리고 Windows 밖(다른 컴퓨터)에서는 바로 접속되지 않습니다.
`netsh portproxy`로 Windows가 WSL로 전달해주는 다리를 하나 놓아야 합니다.

---

## 0. 준비 — 컴퓨터의 IP 확인

Windows PowerShell에서:

```powershell
ipconfig
```

**이더넷 어댑터**의 IPv4 주소를 확인합니다 (예: `10.10.21.23`).
`vEthernet (WSL ...)` 항목은 WSL 내부 전용 주소라 쓰지 않습니다.

---

## 1. WSL 안에서 Streamlit 실행

```bash
cd ~/work/프로젝트폴더
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

여러 프로젝트를 동시에 띄우려면 포트를 다르게 지정합니다 (예: 8501, 8502).

---

## 2. WSL 내부 IP 확인

WSL 터미널에서:

```bash
hostname -I
```

나온 IP(예: `172.25.100.134`)를 메모해둡니다.

> ⚠️ **이 IP는 WSL을 재시작(`wsl --shutdown`, 컴퓨터 재부팅 등)하면 바뀔 수 있습니다.**


---

## 3. Windows PowerShell을 "관리자 권한"으로 실행 후 포트 연결

```powershell
netsh interface portproxy add v4tov4 listenport=8501 listenaddress=0.0.0.0 connectport=8501 connectaddress=172.25.100.134
```

`8501`은 실제 사용하는 포트로, WSL IP는 2단계에서 확인한 값으로 바꿉니다.

**이미 등록된 규칙이 있다면 먼저 삭제 후 재등록:**

```powershell
netsh interface portproxy delete v4tov4 listenport=8501 listenaddress=0.0.0.0
netsh interface portproxy add v4tov4 listenport=8501 listenaddress=0.0.0.0 connectport=8501 connectaddress=172.25.100.134
```

**등록된 규칙 확인:**

```powershell
netsh interface portproxy show v4tov4
```

---

## 4. 방화벽 인바운드 규칙 추가

같은 관리자 PowerShell에서:

```powershell
New-NetFirewallRule -DisplayName "Streamlit App" -Direction Inbound -LocalPort 8501 -Protocol TCP -Action Allow
```

여러 프로젝트를 운영 중이면 `-DisplayName`을 프로젝트별로 다르게 지정합니다.

---

## 5. 다른 기기에서 접속

같은 네트워크(Wi-Fi 또는 유선)에 연결된 컴퓨터나 휴대폰 브라우저에서:

```
http://10.10.21.23:8501
```

발표 컴퓨터의 이더넷 IP + 포트 번호로 접속합니다.
휴대폰은 모바일 데이터가 아니라 **같은 Wi-Fi**에 연결되어 있어야 합니다.

---

## 종료 후 정리 (선택)

```powershell
netsh interface portproxy delete v4tov4 listenport=8501 listenaddress=0.0.0.0
Remove-NetFirewallRule -DisplayName "Streamlit App"
```

---

---

## 참고 — 더 간단한 대안 (Windows 11 + 최신 WSL)

WSL이 "미러 네트워킹 모드"를 지원하면 portproxy 없이 훨씬 간단하게 설정할 수 있습니다.

`C:\Users\사용자명\.wslconfig` 파일 생성:

```ini
[wsl2]
networkingMode=mirrored
```

저장 후 PowerShell에서:

```powershell
wsl --shutdown
```

다시 WSL을 켜고 Streamlit을 `0.0.0.0`으로 실행하면, 방화벽 규칙(4단계)만 추가해도
바로 `http://이더넷IP:포트`로 다른 기기에서 접속됩니다.

지원 여부 확인:

```powershell
wsl --version
```

---

## 참고 — 완전히 다른 네트워크(원격지)에서 접속해야 하는 경우

같은 네트워크가 아니라 외부에서도 접속해야 한다면, 공유기 포트포워딩 설정이나
[ngrok](https://ngrok.com/) 같은 임시 터널링 도구를 사용합니다. ngrok은 공유기
설정 없이 즉시 공개 URL을 만들어주며, 발표처럼 일회성으로 쓸 때 편리합니다.

```bash
ngrok http 8501
```

⚠️ 외부에 공개하는 경우, 로그인 계정 정보가 노출되지 않도록 주의하고
발표가 끝나면 바로 종료하는 것을 권장합니다.
