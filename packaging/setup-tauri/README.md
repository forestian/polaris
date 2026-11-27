# Polaris 설치 마법사 (Tauri)

목업(`Polaris 설치 마법사.html`) 디자인을 **그대로** 구현하는 Tauri 기반 Windows 설치기.
현재는 **UI 셸**만 완성 — 실제 설치 동작은 후속 단계.

## 구조
```
packaging/setup-tauri/
├── index.html            # :root 색 토큰 + 폰트 + 루트
├── src/
│   ├── main.jsx          # React 진입
│   ├── App.jsx           # 설치 마법사 UI (목업 그대로 이식)
│   └── PolarisStar.jsx   # 좌측 브랜드 패널 별 일러스트
├── src-tauri/
│   ├── tauri.conf.json   # 창 820×612 · 프레임리스 · 비리사이즈 · 중앙
│   ├── Cargo.toml        # Tauri 2 (bundle 비활성 → 단일 exe 가 설치기)
│   ├── build.rs
│   ├── src/main.rs       # 진입점 (설치 command 는 추후 추가)
│   └── icons/
└── package.json
```

## 개발 / 빌드 (요구사항)
빌드에는 **Rust 툴체인 + MSVC Build Tools**(Windows 링커)가 필요하다.
- Rust: <https://rustup.rs> (`rustup-init.exe`, 사용자 설치 가능)
- MSVC: "Visual Studio Build Tools" 의 *C++ build tools* (보통 관리자 권한 필요),
  또는 Visual Studio Community
- WebView2 런타임 (Win11 기본 탑재)

```bash
cd packaging/setup-tauri
npm install
npm run dev            # 브라우저 미리보기(Vite, http://localhost:1430)
npm run tauri dev      # Tauri 창으로 실행 (Rust 필요)
npm run tauri build -- --no-bundle   # → src-tauri/target/release/polaris-setup.exe
```

UI 디자인만 빠르게 확인하려면 `npm run dev` 로 충분 (Rust 불필요).

## 남은 작업 (TODO)
1. **폰트 오프라인 번들** — 현재 index.html 은 Pretendard/Fraunces/JetBrains Mono 를
   CDN 으로 로드(디자인 검증용). 배포 전 로컬 `.woff2` 로 교체 + `@font-face`.
2. **나머지 위저드 화면** — 목업엔 "추가 작업 선택"(4/6) 한 장만 디자인됨.
   라이선스 동의 / 설치 위치 / 시작 메뉴 / 설치 진행 / 완료 화면을 같은 스타일로 추가.
3. **설치 로직 (Rust `#[tauri::command]`)**:
   - 앱 페이로드(onedir) 추출 → `%LocalAppData%\Programs\Polaris`
   - 시작 메뉴 / 바탕화면 `.lnk` 생성
   - 추가/제거(HKCU\…\Uninstall) 등록 + 언인스톨러
   - 업그레이드 시 실행 중 프로세스 종료
4. **코드 서명** (SmartScreen 대응, 선택).

> 빌드 산출물(node_modules/dist/target)은 .gitignore 처리. 소스만 트래킹.
