// 설치 마법사 다국어 문자열 (한국어 / English). 1페이지에서 선택한 언어로 전환.
export const STR = {
  ko: {
    title: 'Polaris Free 설치',
    tagline: '쿠버네티스 · 서버 운영 세션 통합 관리툴',
    steps: ['설치 언어', '설치 위치', '추가 작업', '설치', '완료'],
    stepN: (n, t) => `${n} / ${t} 단계`,

    p0_h: '설치 언어 선택',
    p0_sub: '설치 마법사와 Polaris Free에서 사용할 언어를 선택하세요.',
    lang_ko: '한국어',
    lang_en: 'English',
    lang_ko_d: '설치 마법사를 한국어로 표시합니다.',
    lang_en_d: 'Display the setup wizard in English.',

    p1_h: '설치 위치 선택',
    p1_sub: 'Polaris Free를 설치할 폴더를 선택하세요. 관리자 권한이 필요 없는 사용자 폴더가 기본입니다.',
    p1_label: '설치 폴더',
    browse: '찾아보기',
    p1_note: '사용자 데이터(설정·보관함·kubeconfig)는 설치 폴더와 별도로 %USERPROFILE% 아래에 저장됩니다.',

    p2_h: '추가 작업 선택',
    p2_sub: 'Polaris Free 설치 중 함께 수행할 작업을 선택하세요. 나중에 바꿀 수 있습니다.',
    g_shortcut: '바로 가기 · 자동 실행',
    g_adv: '고급',
    t_desktop: '바탕 화면에 바로 가기 만들기',
    t_desktop_d: '바탕 화면에서 Polaris Free를 바로 실행할 수 있는 아이콘을 추가합니다.',
    t_start: '시작 메뉴에 등록',
    t_start_d: '시작 메뉴 앱 목록에 Polaris Free를 추가합니다.',
    t_auto: 'Windows 시작 시 자동 실행',
    t_auto_d: '로그인하면 Polaris Free 트레이 에이전트가 백그라운드에서 자동으로 시작됩니다.',
    recommended: '권장',


    p3_h: '설치 중',
    p3_sub: 'Polaris Free를 설치하고 있습니다. 잠시만 기다려 주세요.',
    copyLog: '로그 복사',
    copied: '복사됨',
    p3_done: '설치가 완료되었습니다.',

    p4_h: '설치 완료',
    p4_sub: 'Polaris Free 설치가 완료되었습니다. 아래에서 바로 실행할 수 있습니다.',
    runAfter: 'Polaris Free 실행',

    back: '뒤로', next: '다음', install: '설치', finish: '마침',
    cancel: '취소', installing: '설치 중…', retry: '다시 시도',
  },
  en: {
    title: 'Polaris Free Setup',
    tagline: 'Unified Kubernetes & server-ops console',
    steps: ['Language', 'Location', 'Tasks', 'Install', 'Done'],
    stepN: (n, t) => `Step ${n} of ${t}`,

    p0_h: 'Choose language',
    p0_sub: 'Select the language for the setup wizard and Polaris Free.',
    lang_ko: '한국어',
    lang_en: 'English',
    lang_ko_d: '설치 마법사를 한국어로 표시합니다.',
    lang_en_d: 'Display the setup wizard in English.',

    p1_h: 'Choose install location',
    p1_sub: 'Select a folder to install Polaris Free. A per-user folder (no admin required) is the default.',
    p1_label: 'Install folder',
    browse: 'Browse',
    p1_note: 'User data (settings, vault, kubeconfig) is stored under %USERPROFILE%, separate from the install folder.',

    p2_h: 'Select additional tasks',
    p2_sub: 'Choose tasks to perform during installation. You can change these later.',
    g_shortcut: 'Shortcuts · startup',
    g_adv: 'Advanced',
    t_desktop: 'Create a desktop shortcut',
    t_desktop_d: 'Adds an icon to launch Polaris Free from the desktop.',
    t_start: 'Add to Start menu',
    t_start_d: 'Adds Polaris Free to the Start menu app list.',
    t_auto: 'Run at Windows startup',
    t_auto_d: 'The Polaris Free tray agent starts automatically in the background at login.',
    recommended: 'Recommended',


    p3_h: 'Installing',
    p3_sub: 'Installing Polaris Free. Please wait a moment.',
    copyLog: 'Copy log',
    copied: 'Copied',
    p3_done: 'Installation complete.',

    p4_h: 'Installation complete',
    p4_sub: 'Polaris Free has been installed. You can launch it now below.',
    runAfter: 'Launch Polaris Free',

    back: 'Back', next: 'Next', install: 'Install', finish: 'Finish',
    cancel: 'Cancel', installing: 'Installing…', retry: 'Retry',
  },
}
