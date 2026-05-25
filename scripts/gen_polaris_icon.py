"""POLARIS 아이콘 생성 — PolarisMark SVG 의 8각 별을 PIL 로 다시 그려
작업표시줄(.ico) + 트레이(.png) + favicon 으로 사용.

3-tone gold gradient simulation:
  - 외곽 8각 별: dark gold (#a87830)
  - 중간 8각 별: bright gold (#f3c969)
  - 내부 별: cream (#fff5d6)
배경: 미드나잇 인디고 둥근 사각형 (#131734)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT_DIR = Path(__file__).resolve().parent.parent / 'packaging' / 'icons'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def render_polaris_icon(size: int = 256, *, with_background: bool = True) -> Image.Image:
    """polaris 별 아이콘 렌더 (size x size, RGBA).

    SVG 의 점 좌표(40x40 viewBox) 를 size 에 맞게 스케일.
    """
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    s   = size / 40.0   # 40 → size 스케일

    def pts(coords):
        return [(x * s, y * s) for x, y in coords]

    # ── 배경 둥근 사각형 (인디고) ────────────────────────────────────────
    if with_background:
        margin = size * 0.06
        radius = size * 0.18
        d.rounded_rectangle(
            (margin, margin, size - margin, size - margin),
            radius=radius, fill='#131734',
        )

    # ── 후광 (골드 글로우, 큰 사이즈에서만) ──────────────────────────────
    if size >= 64 and with_background:
        halo = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        hd   = ImageDraw.Draw(halo)
        # 흐릿한 큰 원 (골드)
        c = size / 2
        r = size * 0.42
        hd.ellipse((c - r, c - r, c + r, c + r), fill=(243, 201, 105, 80))
        halo = halo.filter(ImageFilter.GaussianBlur(radius=size * 0.08))
        img = Image.alpha_composite(img, halo)
        d = ImageDraw.Draw(img)

    # ── 4축 광선 (큰 사이즈에서만, 옅게) ─────────────────────────────────
    if size >= 64 and with_background:
        # 가로
        ray_w = max(1, int(size * 0.025))
        d.rectangle(
            (margin if with_background else 0, size / 2 - ray_w / 2,
             size - (margin if with_background else 0), size / 2 + ray_w / 2),
            fill=(255, 245, 208, 90),
        )
        # 세로
        d.rectangle(
            (size / 2 - ray_w / 2, margin if with_background else 0,
             size / 2 + ray_w / 2, size - (margin if with_background else 0)),
            fill=(255, 245, 208, 90),
        )

    # ── 메인 8각 별 (외곽: dark gold) ────────────────────────────────────
    main_pts = [(20, 3), (23, 17), (37, 20), (23, 23),
                (20, 37), (17, 23), (3, 20), (17, 17)]
    d.polygon(pts(main_pts), fill='#a87830')

    # ── 중간 별 (bright gold) ────────────────────────────────────────────
    mid_pts = [(20, 6), (22.4, 17.6), (34, 20), (22.4, 22.4),
               (20, 34), (17.6, 22.4), (6, 20), (17.6, 17.6)]
    d.polygon(pts(mid_pts), fill='#f3c969')

    # ── 내부 별 (cream highlight) ────────────────────────────────────────
    inner_pts = [(20, 10), (21.4, 18.6), (30, 20), (21.4, 21.4),
                 (20, 30), (18.6, 21.4), (10, 20), (18.6, 18.6)]
    d.polygon(pts(inner_pts), fill='#fff5d6')

    # ── 중심 점 (어두운 코어, 큰 사이즈에서만) ───────────────────────────
    if size >= 32:
        cr = max(1, size * 0.025)
        d.ellipse((size / 2 - cr, size / 2 - cr, size / 2 + cr, size / 2 + cr),
                  fill='#1a1024')

    return img


def main():
    # 1. ICO — 작업표시줄/EXE 용 (다중 사이즈 임베드)
    ico_path = OUT_DIR / 'polaris.ico'
    sizes_with_bg = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base = render_polaris_icon(256, with_background=True)
    images = [render_polaris_icon(s[0], with_background=True) for s in sizes_with_bg]
    base.save(ico_path, format='ICO', sizes=sizes_with_bg, append_images=images[:-1])
    print(f'✓ {ico_path}  ({ico_path.stat().st_size / 1024:.1f} KB)')

    # 2. PNG 64×64 — 트레이용 (배경 + 별)
    tray = render_polaris_icon(64, with_background=True)
    tray_path = OUT_DIR / 'polaris-tray.png'
    tray.save(tray_path, format='PNG')
    print(f'✓ {tray_path}  ({tray_path.stat().st_size / 1024:.1f} KB)')

    # 3. PNG 256×256 — favicon / 미리보기용
    big = render_polaris_icon(256, with_background=True)
    big_path = OUT_DIR / 'polaris-256.png'
    big.save(big_path, format='PNG')
    print(f'✓ {big_path}  ({big_path.stat().st_size / 1024:.1f} KB)')

    # 4. favicon — ui/public/favicon.ico (Vite 기본 위치)
    favicon_dir = Path(__file__).resolve().parent.parent / 'ui' / 'public'
    favicon_dir.mkdir(parents=True, exist_ok=True)
    favicon_path = favicon_dir / 'favicon.ico'
    base.save(favicon_path, format='ICO', sizes=sizes_with_bg, append_images=images[:-1])
    print(f'✓ {favicon_path}  ({favicon_path.stat().st_size / 1024:.1f} KB)')


if __name__ == '__main__':
    main()
