// Polaris 설치 마법사 (Tauri) — 진입점 + 설치/제거 로직.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::io::Cursor;
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Emitter};
use winreg::enums::*;
use winreg::RegKey;
#[cfg(windows)]
use std::os::windows::process::CommandExt;

// 콘솔 하위프로세스(taskkill/cmd)를 창 없이 실행 — 설치/제거 중 cmd 창 깜빡임 방지
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

// 임베드된 앱 페이로드 (onedir zip). 빌드 시 src-tauri/payload/ 의 zip.
static PAYLOAD: &[u8] = include_bytes!("../payload/polaris-win64.zip");

// 무료판은 정식판(Polaris)과 한 PC 에 같이 깔린다 — 설치 폴더 · 바로 가기 · 레지스트리 이름을 따로 쓴다.
const APP_NAME: &str = "Polaris Free";
const UNINSTALL_KEY: &str = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Polaris Free";
const RUN_KEY: &str = r"Software\Microsoft\Windows\CurrentVersion\Run";
const VERSION: &str = "1.5.74-f1";

// 설치 폴더에 **우리가 넣은 것**의 목록 (v1.3.39). 제거는 이 목록에 있는 것만 지운다.
const MANIFEST: &str = "polaris-install-manifest.txt";
// 목록 파일이 없는 옛 설치(v1.3.38 이전)에서 지울 것 — 페이로드의 최상위 항목들
const LEGACY_ENTRIES: &[&str] = &["polaris.exe", "_internal", "polaris-uninstall.exe"];

// 설치 로그 싱크 — GUI(이벤트) / CLI 테스트(파일) 양쪽에서 재사용.
type LogFn<'a> = dyn Fn(&str) + 'a;

// ── 알려진 폴더 (env 기반, KnownFolder API 회피) ──────────────────────────────
fn desktop_dir() -> Option<PathBuf> {
    std::env::var("USERPROFILE").ok().map(|u| PathBuf::from(u).join("Desktop"))
}
fn startmenu_programs_dir() -> Option<PathBuf> {
    std::env::var("APPDATA").ok().map(|a| PathBuf::from(a).join(r"Microsoft\Windows\Start Menu\Programs"))
}

fn make_lnk(lnk: &Path, target: &Path) {
    if let Ok(sl) = mslnk::ShellLink::new(target) {
        let _ = sl.create_lnk(lnk);
    }
}

// ── 실행 중인 Polaris 끄기 (v1.3.29) ─────────────────────────────────────────
//
// `taskkill` 은 **끝날 때까지 기다려 주지 않는다.** 신호만 보내고 바로 돌아온다.
// 그래서 곧바로 polaris.exe 를 덮어쓰려 하면 아직 프로세스가 남아 있어
// "액세스가 거부되었습니다" 로 한 번 실패했다 — 사용자는 [다시 시도] 를 눌러야
// 했고, 그때는 이미 죽어 있어서 그냥 됐다(사용자 신고).
//
// 고치는 법은 재시도 버튼이 아니라 **끝난 것을 확인하고 넘어가는 것**이다.

/// **이 설치 폴더의** polaris.exe 프로세스 번호들.
///
/// 이름(polaris.exe)으로만 찾으면 같은 PC 의 정식판까지 끈다 — 실행 파일 경로가
/// 설치 폴더 아래인 것만 고른다(PowerShell Get-Process 의 Path).
fn polaris_pids_in(dir: &Path) -> Vec<String> {
    let d = dir.to_string_lossy().replace('/', "\\");
    let d = d.trim_end_matches('\\').replace('\'', "''");
    let script = format!(
        "Get-Process -Name polaris -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -and $_.Path.StartsWith('{d}\\', [System.StringComparison]::OrdinalIgnoreCase) }} | ForEach-Object {{ $_.Id }}"
    );
    let out = std::process::Command::new("powershell")
        .args(["-NoProfile", "-NonInteractive", "-Command", &script])
        .creation_flags(CREATE_NO_WINDOW)
        .output();
    match out {
        Ok(o) => String::from_utf8_lossy(&o.stdout)
            .lines()
            .map(|l| l.trim().to_string())
            .filter(|l| !l.is_empty() && l.chars().all(|c| c.is_ascii_digit()))
            .collect(),
        Err(_) => Vec::new(),
    }
}

/// 이 설치 폴더의 Polaris 가 실행 중이면 끄고, **정말로 끝날 때까지** 기다린다. 끝났으면 true.
fn kill_polaris_and_wait(log: &LogFn, dir: &Path) -> bool {
    let pids = polaris_pids_in(dir);
    if pids.is_empty() {
        return true;
    }
    log("Polaris Free 가 실행 중입니다 — 종료하고 이어서 진행합니다.");
    for pid in &pids {
        let _ = std::process::Command::new("taskkill")
            .args(["/F", "/T", "/PID", pid])
            .creation_flags(CREATE_NO_WINDOW)
            .output();
    }

    // 최대 15초. 프로세스가 사라져도 파일 핸들이 잠깐 남을 수 있어 조금 더 둔다.
    for _ in 0..60 {
        if polaris_pids_in(dir).is_empty() {
            std::thread::sleep(std::time::Duration::from_millis(400));
            log("종료를 확인했습니다.");
            return true;
        }
        std::thread::sleep(std::time::Duration::from_millis(100));
    }
    log("경고: Polaris Free 가 아직 종료되지 않았습니다 — 그래도 계속합니다.");
    false
}

/// 파일 하나를 만든다. 잠겨 있으면 잠깐 기다렸다 다시 해 본다.
///
/// 프로세스가 사라진 뒤에도 백신·검색 인덱서가 방금 풀린 파일을 잠시 붙잡는 일이
/// 있다. 그때 한 번 실패하고 설치 전체를 되돌리는 것은 과하다.
fn create_file_retry(path: &Path) -> std::io::Result<fs::File> {
    let mut last = None;
    for i in 0..12 {
        match fs::File::create(path) {
            Ok(f) => return Ok(f),
            Err(e) => {
                last = Some(e);
                std::thread::sleep(std::time::Duration::from_millis(150 + i * 50));
            }
        }
    }
    Err(last.unwrap_or_else(|| std::io::Error::new(
        std::io::ErrorKind::Other, "파일을 만들지 못했습니다")))
}

// ── Tauri 커맨드 ─────────────────────────────────────────────────────────────
/// `--dir <설치 폴더>` 로 띄우면 그 폴더를 기본값으로 — 기본 위치가 아닌 곳에
/// 설치해 둔 사람이 다시 설치하면서 기본 폴더에 두 번째 Polaris 가 생기지 않게.
fn dir_from_args(args: &[String]) -> Option<String> {
    let pos = args.iter().position(|a| a == "--dir")?;
    let d = args.get(pos + 1)?.trim();
    if d.is_empty() || d.starts_with("--") {
        return None;
    }
    Some(d.to_string())
}

#[tauri::command]
fn default_install_dir() -> String {
    let args: Vec<String> = std::env::args().collect();
    if let Some(d) = dir_from_args(&args) {
        return d;
    }
    let base = std::env::var("LOCALAPPDATA").unwrap_or_else(|_| "C:\\".into());
    format!("{}\\Programs\\{}", base, APP_NAME)
}

#[tauri::command]
fn pick_install_dir(current: String) -> Option<String> {
    let mut dlg = rfd::FileDialog::new().set_title("Polaris Free 설치 폴더 선택");
    if !current.is_empty() {
        if let Some(parent) = Path::new(&current).parent() {
            if parent.exists() {
                dlg = dlg.set_directory(parent);
            }
        }
    }
    dlg.pick_folder()
        .map(ensure_polaris_subdir)
        .map(|p| p.to_string_lossy().replace('/', "\\"))
}

/// 고른 폴더 이름이 `Polaris Free` 가 아니면 그 **아래에** `Polaris Free` 를 만든다 (v1.3.39).
///
/// 예전에는 고른 폴더에 그대로 풀었고, 제거는 그 폴더를 `rmdir /s /q` 로 통째로
/// 지웠다. `D:\Tools` 를 고르면 **그 안의 다른 프로그램까지 전부** 지워지는 구조였다.
/// 다른 설치기들이 하는 것처럼 전용 하위 폴더를 둔다.
fn ensure_polaris_subdir(p: PathBuf) -> PathBuf {
    let named = p
        .file_name()
        .map(|n| n.to_string_lossy().eq_ignore_ascii_case(APP_NAME))
        .unwrap_or(false);
    if named { p } else { p.join(APP_NAME) }
}

/// 목록 파일의 한 줄로 받아도 되는 이름인가 — **설치 폴더 바로 아래의 이름 하나**만.
/// 목록 파일은 사용자가 쓸 수 있는 폴더에 있으므로 `..\..` 같은 줄을 믿지 않는다.
fn safe_entry(name: &str) -> bool {
    let n = name.trim();
    !n.is_empty()
        && n != "."
        && n != ".."
        && !n.contains(['/', '\\', ':', '*', '?', '"', '<', '>', '|'])
}

/// 제거할 항목 — 목록 파일이 있으면 그것, 없으면 옛 설치의 고정 목록.
fn uninstall_entries(dir: &Path) -> Vec<String> {
    match fs::read_to_string(dir.join(MANIFEST)) {
        Ok(s) => s.lines().map(|l| l.trim().to_string()).filter(|l| safe_entry(l)).collect(),
        Err(_) => LEGACY_ENTRIES.iter().map(|s| s.to_string()).collect(),
    }
}

/// `dir` 아래의 `entries` 만 지운다(`skip` 은 건너뛴다 — 실행 중인 제거기 자신).
/// 폴더 자체는 지우지 않는다 — 비었을 때만 나중에 `rmdir`(재귀 아님)로 지운다.
fn remove_entries(dir: &Path, entries: &[String], skip: Option<&Path>) {
    for name in entries {
        if !safe_entry(name) {
            continue;
        }
        let p = dir.join(name);
        if let Some(s) = skip {
            if same_path(&p, s) {
                continue;
            }
        }
        if p.is_dir() {
            let _ = fs::remove_dir_all(&p);
        } else if p.exists() {
            let _ = fs::remove_file(&p);
        }
    }
}

fn same_path(a: &Path, b: &Path) -> bool {
    let norm = |p: &Path| p.to_string_lossy().replace('/', "\\").to_lowercase();
    match (fs::canonicalize(a), fs::canonicalize(b)) {
        (Ok(x), Ok(y)) => x == y,
        _ => norm(a) == norm(b),
    }
}

#[tauri::command]
fn launch_polaris(dir: String) -> Result<(), String> {
    let exe = PathBuf::from(&dir).join("polaris.exe");
    std::process::Command::new(exe)
        .spawn()
        .map(|_| ())
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn do_install(
    app: AppHandle,
    dir: String,
    desktop: bool,
    startmenu: bool,
    autostart: bool,
) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        let log = move |m: &str| { let _ = app.emit("install-log", m.to_string()); };
        run_install(&log, &dir, desktop, startmenu, autostart)
    })
    .await
    .map_err(|e| e.to_string())?
}

fn run_install(
    log: &LogFn,
    dir: &str,
    desktop: bool,
    startmenu: bool,
    autostart: bool,
) -> Result<(), String> {
    let install = PathBuf::from(dir);
    log(&format!("설치 폴더: {dir}"));

    // 업그레이드 — 실행 중 인스턴스를 끄고 **정말로 끝날 때까지 기다린다**.
    // 기다리지 않으면 아래 파일 복사가 첫 판에 실패한다(v1.3.29 에서 고침).
    kill_polaris_and_wait(log, &install);

    fs::create_dir_all(&install).map_err(|e| format!("폴더 생성 실패: {e}"))?;

    // 페이로드(zip) 해제 — 선행 "polaris/" 경로 제거
    let mut zip = zip::ZipArchive::new(Cursor::new(PAYLOAD)).map_err(|e| format!("zip 열기 실패: {e}"))?;
    let total = zip.len();
    log(&format!("애플리케이션 파일 {total}개 압축 해제..."));
    // 이번에 넣는 최상위 항목들 — 제거할 때 이것만 지운다
    let mut top: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    for i in 0..total {
        let mut f = zip.by_index(i).map_err(|e| e.to_string())?;
        let enclosed = match f.enclosed_name() {
            Some(p) => p,
            None => continue,
        };
        let rel: PathBuf = enclosed.components().skip(1).collect(); // "polaris/" 제거
        if rel.as_os_str().is_empty() {
            continue;
        }
        if let Some(first) = rel.components().next() {
            top.insert(first.as_os_str().to_string_lossy().to_string());
        }
        let out = install.join(&rel);
        if f.is_dir() {
            let _ = fs::create_dir_all(&out);
        } else {
            if let Some(p) = out.parent() {
                let _ = fs::create_dir_all(p);
            }
            let mut o = create_file_retry(&out).map_err(|e| format!("{} — {e}", rel.display()))?;
            std::io::copy(&mut f, &mut o).map_err(|e| e.to_string())?;
        }
        if i % 50 == 0 || i + 1 == total {
            log(&format!("  ({}/{}) {}", i + 1, total, rel.display()));
        }
    }
    log("파일 복사 완료.");

    let exe = install.join("polaris.exe");

    // 언인스톨러 = 설치기 자신 복사본
    let uninst = install.join("polaris-uninstall.exe");
    if let Ok(self_exe) = std::env::current_exe() {
        let _ = fs::copy(&self_exe, &uninst);
    }

    // 넣은 것의 목록 — 업그레이드면 예전 목록과 합친다(예전 버전만 넣던 항목도 지우도록)
    top.insert("polaris-uninstall.exe".into());
    top.insert(MANIFEST.into());
    if install.join(MANIFEST).exists() {
        for e in uninstall_entries(&install) {
            top.insert(e);
        }
    }
    let body: String = top.iter().filter(|e| safe_entry(e)).map(|e| format!("{e}\n")).collect();
    if let Err(e) = fs::write(install.join(MANIFEST), body) {
        log(&format!("설치 목록 저장 실패: {e} — 제거 시 기본 항목만 지웁니다."));
    }

    // 바로 가기
    if desktop {
        if let Some(d) = desktop_dir() {
            make_lnk(&d.join(format!("{APP_NAME}.lnk")), &exe);
            log("바탕 화면 바로 가기 생성.");
        }
    }
    if startmenu {
        if let Some(p) = startmenu_programs_dir() {
            let grp = p.join(APP_NAME);
            let _ = fs::create_dir_all(&grp);
            make_lnk(&grp.join(format!("{APP_NAME}.lnk")), &exe);
            make_lnk(&grp.join(format!("{APP_NAME} 제거.lnk")), &uninst);
            log("시작 메뉴 등록.");
        }
    }

    // 자동 실행 (HKCU Run)
    let hkcu = RegKey::predef(HKEY_CURRENT_USER);
    if autostart {
        if let Ok((k, _)) = hkcu.create_subkey(RUN_KEY) {
            let _ = k.set_value(APP_NAME, &format!("\"{}\"", exe.display()));
            log("Windows 시작 시 자동 실행 등록.");
        }
    } else if let Ok(k) = hkcu.open_subkey_with_flags(RUN_KEY, KEY_SET_VALUE) {
        let _ = k.delete_value(APP_NAME);
    }

    // 추가/제거 등록 (HKCU Uninstall)
    if let Ok((k, _)) = hkcu.create_subkey(UNINSTALL_KEY) {
        let _ = k.set_value("DisplayName", &APP_NAME);
        let _ = k.set_value("DisplayVersion", &VERSION);
        let _ = k.set_value("Publisher", &"Polaris");
        let _ = k.set_value("InstallLocation", &install.to_string_lossy().to_string());
        let _ = k.set_value("DisplayIcon", &exe.to_string_lossy().to_string());
        let _ = k.set_value("UninstallString", &format!("\"{}\" --uninstall", uninst.display()));
        let _ = k.set_value("NoModify", &1u32);
        let _ = k.set_value("NoRepair", &1u32);
        log("추가/제거 항목 등록.");
    }

    log("설치 완료.");
    Ok(())
}

// ── 제거 모드 (polaris-uninstall.exe --uninstall) ────────────────────────────
fn run_uninstall() {
    let hkcu = RegKey::predef(HKEY_CURRENT_USER);
    let install: Option<PathBuf> = hkcu
        .open_subkey(UNINSTALL_KEY)
        .ok()
        .and_then(|k| k.get_value::<String, _>("InstallLocation").ok())
        .map(PathBuf::from);

    // 실행 중 종료(이 설치 폴더의 것만) — 여기서도 기다린다. 안 기다리면 폴더 삭제가 반쯤 실패한다.
    if let Some(dir) = &install {
        kill_polaris_and_wait(&|_s: &str| {}, dir);
    }

    // 바로 가기 제거
    if let Some(d) = desktop_dir() {
        let _ = fs::remove_file(d.join(format!("{APP_NAME}.lnk")));
    }
    if let Some(p) = startmenu_programs_dir() {
        let _ = fs::remove_dir_all(p.join(APP_NAME));
    }
    // 레지스트리 제거
    let _ = hkcu.delete_subkey_all(UNINSTALL_KEY);
    if let Ok(k) = hkcu.open_subkey_with_flags(RUN_KEY, KEY_SET_VALUE) {
        let _ = k.delete_value(APP_NAME);
    }

    // 사용자 데이터 보존 안내
    let prof = std::env::var("USERPROFILE").unwrap_or_default();
    rfd::MessageDialog::new()
        .set_title("Polaris Free 제거")
        .set_description(format!(
            "Polaris Free 가 제거되었습니다.\n\n사용자 데이터는 안전을 위해 삭제하지 않고 그대로 두었습니다:\n  {prof}\\.polaris-free  (설정·보안 보관함·스냅샷)\n  {prof}\\.kube  (kubeconfig·k9s·helm 등)\n\n완전히 삭제하려면 위 폴더를 직접 지우세요."
        ))
        .set_level(rfd::MessageLevel::Info)
        .show();

    // 설치 폴더 정리 — **우리가 넣은 것만** 지운다 (v1.3.39).
    // 예전에는 폴더를 `rmdir /s /q` 로 통째로 지워, 설치할 때 `D:\Tools` 처럼 다른
    // 파일이 있는 폴더를 골랐다면 그것까지 전부 사라졌다.
    if let Some(dir) = install {
        let me = std::env::current_exe().ok();
        let entries = uninstall_entries(&dir);
        remove_entries(&dir, &entries, me.as_deref());
        // 실행 중인 제거기 자신은 지연 삭제. 폴더는 **비어 있을 때만** 지운다
        // (`rmdir` 에 /s 가 없으면 빈 폴더만 지운다).
        let mut cmd = String::from("timeout /t 2 /nobreak >nul");
        if let Some(m) = &me {
            if m.parent().map(|p| same_path(p, &dir)).unwrap_or(false) {
                cmd.push_str(&format!(" & del /f /q \"{}\"", m.display()));
            }
        }
        cmd.push_str(&format!(" & rmdir \"{}\"", dir.display()));
        let _ = std::process::Command::new("cmd").args(["/C", &cmd]).creation_flags(CREATE_NO_WINDOW).spawn();
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--uninstall") {
        run_uninstall();
        return;
    }
    // 헤드리스 설치 검증 (개발용): --install-test <dir>
    // GUI 없이 do_install 과 동일 코드(run_install)를 실행, 로그는 stdout + 파일.
    if let Some(pos) = args.iter().position(|a| a == "--install-test") {
        let dir = args.get(pos + 1).cloned().unwrap_or_else(default_install_dir);
        let logpath = std::env::temp_dir().join("polaris-install-test.log");
        let _ = std::fs::write(&logpath, "");
        let logf = move |m: &str| {
            use std::io::Write;
            if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(&logpath) {
                let _ = writeln!(f, "{m}");
            }
        };
        // 헤드리스 검증은 **둘 다 켜서** 돈다 — 설치 경로 전체(기능 선택 파일
        // 기록까지)를 지나가는 것이 목적이라 꺼 두면 그 줄을 안 밟는다.
        let r = run_install(&logf, &dir, true, true, false);
        let _ = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(std::env::temp_dir().join("polaris-install-test.log"))
            .map(|mut f| { use std::io::Write; let _ = writeln!(f, "RESULT: {:?}", r); });
        return;
    }
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            default_install_dir,
            pick_install_dir,
            launch_polaris,
            do_install
        ])
        .run(tauri::generate_context!())
        .expect("Polaris 설치 마법사 실행 중 오류");
}

#[cfg(test)]
mod tests {
    use super::*;

    // v1.3.74 — zip 크레이트를 2 → 9 로 올렸다(2.x 전부 회수). 실제로 넣은 페이로드를
    // 설치할 때와 같은 방법으로 끝까지 풀어 본다(디스크엔 안 쓴다).
    #[test]
    fn payload_unpacks_with_current_zip_crate() {
        let mut zip = zip::ZipArchive::new(Cursor::new(PAYLOAD)).expect("zip 열기");
        assert!(zip.len() > 10, "페이로드가 비어 있다");
        let (mut files, mut bytes, mut has_exe) = (0usize, 0u64, false);
        for i in 0..zip.len() {
            let mut f = zip.by_index(i).expect("항목");
            let name = f.enclosed_name().expect("밖으로 나가는 이름이 없어야 한다");
            if name.ends_with("polaris.exe") { has_exe = true; }
            if !f.is_dir() {
                let want = f.size();
                let got = std::io::copy(&mut f, &mut std::io::sink()).expect("압축 풀기");
                assert_eq!(got, want, "{}", name.display());
                files += 1;
                bytes += got;
            }
        }
        assert!(has_exe, "polaris.exe 가 없다");
        assert!(files > 10 && bytes > 10_000_000, "files={files} bytes={bytes}");
    }

    #[test]
    fn dir_arg_from_command_line() {
        let a = |v: &[&str]| v.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        assert_eq!(dir_from_args(&a(&["setup.exe", "--dir", r"D:\Tools\Polaris"])),
                   Some(r"D:\Tools\Polaris".to_string()));
        assert_eq!(dir_from_args(&a(&["setup.exe"])), None);
        assert_eq!(dir_from_args(&a(&["setup.exe", "--dir"])), None);
        assert_eq!(dir_from_args(&a(&["setup.exe", "--dir", "--uninstall"])), None);
        assert_eq!(dir_from_args(&a(&["setup.exe", "--dir", "  "])), None);
    }

    #[test]
    fn subdir_is_added_unless_already_polaris() {
        assert_eq!(ensure_polaris_subdir(PathBuf::from(r"D:\Tools")), PathBuf::from(r"D:\Tools\Polaris Free"));
        assert_eq!(ensure_polaris_subdir(PathBuf::from(r"C:\x\Polaris Free")), PathBuf::from(r"C:\x\Polaris Free"));
        assert_eq!(ensure_polaris_subdir(PathBuf::from(r"C:\x\polaris free")), PathBuf::from(r"C:\x\polaris free"));
        // 정식판 폴더를 골라도 그 안에 섞지 않는다
        assert_eq!(ensure_polaris_subdir(PathBuf::from(r"C:\x\Polaris")), PathBuf::from(r"C:\x\Polaris\Polaris Free"));
    }

    #[test]
    fn manifest_lines_cannot_escape() {
        for bad in ["", "..", ".", r"..\..\Users", "a/b", r"C:\Windows", "x:y", "  "] {
            assert!(!safe_entry(bad), "{bad:?} 를 받으면 안 된다");
        }
        for ok in ["polaris.exe", "_internal", MANIFEST] {
            assert!(safe_entry(ok));
        }
    }

    #[test]
    fn uninstall_keeps_files_we_did_not_put() {
        let root = std::env::temp_dir().join(format!("polaris-uninst-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join("_internal").join("sub")).unwrap();
        fs::write(root.join("_internal").join("sub").join("a.dll"), "x").unwrap();
        fs::write(root.join("polaris.exe"), "x").unwrap();
        fs::write(root.join("someone-elses.txt"), "keep").unwrap();
        fs::create_dir_all(root.join("OtherApp")).unwrap();
        fs::write(root.join(MANIFEST), "polaris.exe\n_internal\n..\\OtherApp\n").unwrap();

        let entries = uninstall_entries(&root);
        assert_eq!(entries, vec!["polaris.exe".to_string(), "_internal".to_string()]);
        remove_entries(&root, &entries, None);

        assert!(!root.join("polaris.exe").exists());
        assert!(!root.join("_internal").exists());
        assert!(root.join("someone-elses.txt").exists(), "남의 파일은 남아야 한다");
        assert!(root.join("OtherApp").exists(), "남의 폴더는 남아야 한다");
        let _ = fs::remove_dir_all(&root);
    }

    #[test]
    fn legacy_install_without_manifest_uses_fixed_list() {
        let root = std::env::temp_dir().join(format!("polaris-uninst-legacy-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(&root).unwrap();
        let e = uninstall_entries(&root);
        assert!(e.contains(&"polaris.exe".to_string()) && e.contains(&"_internal".to_string()));
        let _ = fs::remove_dir_all(&root);
    }
}
