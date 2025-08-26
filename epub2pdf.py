# -*- coding: utf-8 -*-
"""
EPUB → 벡터 PDF 변환기 (페이지 크기 지정 지원)
- 기본 엔진: Chromium(Playwright)  ─ Windows 의존성 없음
- 옵션 엔진: WeasyPrint            ─ OS 네이티브 DLL 필요(권장X)
- --split  : 챕터별 PDF 생성 후 병합(대용량 안정)
- --page   : 페이지 크기(A4/B5/7x9in/사용자정의 178x229mm 등)
- --margin : 여백(mm/in/cm/px), 기본 0 (꽉 차게)

필요:
  pip install playwright bs4 lxml pypdf tqdm
  python -m playwright install chromium
"""

import argparse
import re
import tempfile
import zipfile
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from bs4 import BeautifulSoup
from pypdf import PdfReader, PdfWriter
from tqdm import tqdm
from playwright.sync_api import sync_playwright, Error as PWError

# -----------------------------
# 페이지 크기 파서/프리셋
# -----------------------------
PRESETS = {
    "a4":       ("210mm", "297mm"),
    "letter":   ("8.5in", "11in"),
    "a5":       ("148mm", "210mm"),
    "b5":       ("176mm", "250mm"),
    "oreilly":  ("7in", "9in"),   # 7×9 inch
}

SIZE_RE = re.compile(
    r"^\s*(?P<w>\d+(?:\.\d+)?)\s*x\s*(?P<h>\d+(?:\.\d+)?)\s*(?P<u>mm|cm|in|px)\s*$",
    re.IGNORECASE
)

def parse_page_arg(page_str: str) -> Optional[Tuple[str, str]]:
    """
    --page 문자열을 (width, height)로 변환.
    반환값이 None이면 CSS(@page size) 사용을 의미.
    """
    if not page_str:
        return PRESETS["a4"]
    key = page_str.strip().lower()
    if key == "css":
        return None
    if key in PRESETS:
        return PRESETS[key]
    m = SIZE_RE.match(key)
    if m:
        w = f"{m.group('w')}{m.group('u')}"
        h = f"{m.group('h')}{m.group('u')}"
        return (w, h)
    raise ValueError(
        f"--page 형식이 잘못되었습니다: {page_str}\n"
        "예) a4, b5, oreilly, 7x9in, 178x229mm"
    )

def normalize_margin(margin: str) -> str:
    # '0'만 주면 '0mm'로
    s = margin.strip().lower()
    if s == "0":
        return "0mm"
    if re.match(r"^\d+(\.\d+)?(mm|cm|in|px)$", s):
        return s
    raise ValueError("--margin 은 예) 0mm, 10mm, 0.5in, 12px 형식이어야 합니다.")

# -----------------------------
# EPUB 유틸
# -----------------------------
def as_file_uri(p: Path) -> str:
    return p.resolve().as_uri()

def unzip_epub(epub_path: Path, out_dir: Path) -> None:
    print(f"[INFO] EPUB 압축 해제: {epub_path.name} → {out_dir}")
    with zipfile.ZipFile(epub_path, "r") as zf:
        zf.extractall(out_dir)

def find_opf(root_dir: Path) -> Path:
    container = root_dir / "META-INF" / "container.xml"
    if not container.exists():
        raise FileNotFoundError("META-INF/container.xml 없음")
    soup = BeautifulSoup(container.read_bytes(), "xml")
    rootfile = soup.find("rootfile")
    if not rootfile or not rootfile.get("full-path"):
        raise FileNotFoundError("container.xml에서 OPF 경로 찾기 실패")
    opf_path = (root_dir / rootfile["full-path"]).resolve()
    print(f"[INFO] OPF 경로: {opf_path}")
    return opf_path

def parse_opf(opf_path: Path) -> Tuple[List[str], Dict[str, str], Dict[str, str]]:
    soup = BeautifulSoup(opf_path.read_bytes(), "xml")
    manifest = soup.find("manifest")
    spine = soup.find("spine")

    id_to_href: Dict[str, str] = {}
    id_to_media: Dict[str, str] = {}
    for item in manifest.find_all("item"):
        id_to_href[item["id"]] = item.get("href", "")
        id_to_media[item["id"]] = item.get("media-type", "")

    spine_hrefs: List[str] = []
    for itemref in spine.find_all("itemref"):
        iid = itemref.get("idref")
        if iid and iid in id_to_href:
            spine_hrefs.append(id_to_href[iid])

    print(f"[INFO] 본문(스파인) 파일 수: {len(spine_hrefs)}")
    return spine_hrefs, id_to_href, id_to_media

URL_ATTRS = [
    ("img", "src"),
    ("image", "href"),
    ("link", "href"),
    ("script", "src"),
    ("source", "src"),
    ("video", "src"),
    ("audio", "src"),
]

def absolutize_urls(html_bytes: bytes, base_dir: Path) -> bytes:
    soup = BeautifulSoup(html_bytes, "lxml")
    for tag, attr in URL_ATTRS:
        for el in soup.find_all(tag):
            if el.has_attr(attr):
                href = el.get(attr)
                if not href:
                    continue
                if re.match(r"^(#|https?://|data:|file:)", href):
                    continue
                abs_path = (base_dir / href).resolve()
                if abs_path.exists():
                    el[attr] = as_file_uri(abs_path)
    # xlink:href 처리
    for el in soup.find_all(True):
        xhref = el.get("xlink:href")
        if xhref and not re.match(r"^(#|https?://|data:|file:)", xhref):
            abs_path = (base_dir / xhref).resolve()
            if abs_path.exists():
                el["xlink:href"] = as_file_uri(abs_path)
    return soup.encode(formatter="minimal")

def build_extra_css(page_size: Optional[Tuple[str, str]], margin: str) -> str:
    """동적으로 @page size/margin 포함한 CSS 생성"""
    size_rule = f"size: {page_size[0]} {page_size[1]};" if page_size else ""
    return f"""
@page {{
  {size_rule}
  margin: {margin};
}}
html, body {{ margin: 0; padding: 0; }}
/* 중첩 body 보정 */
body body {{ margin: 0 !important; padding: 0 !important; }}
/* 제목 여백 최소화(원하면 조절) */
h1 {{ font-size: 1.6em; margin: .3em 0; }}
h2 {{ font-size: 1.3em; margin: .35em 0 .2em; }}
h3 {{ font-size: 1.15em; margin: .3em 0 .15em; }}
/* 챕터 구분 */
section.epub-chapter {{ page-break-before: always; }}
/* 미디어는 컨테이너 넘지 않게 */
img, svg, video, canvas {{ max-width: 100%; height: auto; }}
/* 링크 밑줄 제거 */
a {{ text-decoration: none; }}
a:link:after {{ content: ""; }}
@media print {{
  body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
}}
""".strip()

def collect_css(manifest_map: Dict[str, str], media_map: Dict[str, str]) -> List[str]:
    css_hrefs = []
    for iid, href in manifest_map.items():
        if media_map.get(iid, "").lower().startswith("text/css"):
            css_hrefs.append(href)
    print(f"[INFO] CSS 파일 수: {len(css_hrefs)}")
    return css_hrefs

def build_single_html(
    opf_path: Path,
    spine_hrefs: List[str],
    css_hrefs: List[str],
    extra_css: str,
) -> Tuple[str, Path]:
    """스파인 순서대로 이어붙인 하나의 HTML 생성 (여백/페이지 크기 CSS 포함)"""
    opf_dir = opf_path.parent
    html_parts: List[str] = []

    # 전역 CSS 링크(파일 URI)
    css_links = []
    for css in css_hrefs:
        css_path = (opf_dir / css).resolve()
        if css_path.exists():
            css_links.append(f'<link rel="stylesheet" href="{as_file_uri(css_path)}" />')

    for idx, rel in enumerate(spine_hrefs, start=1):
        chapter_path = (opf_dir / rel).resolve()
        if not chapter_path.exists():
            print(f"[WARN] 챕터 없음: {rel}")
            continue
        raw = chapter_path.read_bytes()
        fixed = absolutize_urls(raw, chapter_path.parent)
        soup = BeautifulSoup(fixed, "lxml")

        # 제목
        title_text = None
        if soup.title and soup.title.string:
            title_text = str(soup.title.string).strip()
        h1 = soup.find(["h1", "h2", "h3"])
        if not title_text and h1 and h1.get_text(strip=True):
            title_text = h1.get_text(strip=True)

        body = soup.body or soup
        # 핵심: 중첩 <body>를 그대로 넣지 말고 자식만 넣는다
        body_html = "".join(str(child) for child in (body.contents or []))

        # 표지 추정(1장 또는 파일명에 cover 포함) → 제목 숨김+풀블리드
        is_cover = (idx == 1) or ("cover" in rel.lower())
        section_cls = "epub-chapter fullbleed" if is_cover else "epub-chapter"

        chapter_html = [f'<section class="{section_cls}" id="chap-{idx}">']
        if title_text and not is_cover:
            chapter_html.append(f"<h1>{title_text}</h1>")
        chapter_html.append(body_html)
        chapter_html.append("</section>")
        html_parts.append("".join(chapter_html))

    doc = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
{''.join(css_links)}
<style>
{extra_css}
section.fullbleed, section.cover {{
  width: 100vw; height: 100vh; display: grid; place-items: center;
}}
section.fullbleed img, section.cover img,
section.fullbleed svg, section.cover svg {{
  width: 100vw; height: 100vh; object-fit: contain;
}}
</style>
<title>EPUB Export</title>
</head>
<body>
{''.join(html_parts)}
</body>
</html>"""
    return doc, opf_dir

# -----------------------------
# PDF 작성기 (Chromium)
# -----------------------------
def write_pdf_with_chromium(
    html_str: str, base_url: Path, out_pdf: Path,
    page_size: Optional[Tuple[str, str]], margin: str
) -> None:
    tmp_html = out_pdf.with_suffix(".tmp.html")
    tmp_html.write_text(html_str, encoding="utf-8")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                "--allow-file-access-from-files",
                "--disable-web-security",
                "--disable-gpu",
            ])
            page = browser.new_page()
            page.goto(tmp_html.resolve().as_uri(), timeout=0)
            page.wait_for_timeout(100)
            page.emulate_media(media="print")

            pdf_kwargs = dict(
                path=str(out_pdf),
                print_background=True,
                margin={"top": margin, "right": margin, "bottom": margin, "left": margin},
            )
            if page_size is None:
                # CSS @page size를 신뢰
                pdf_kwargs["prefer_css_page_size"] = True
            else:
                # 너비/높이를 직접 지정, CSS보다 우선
                pdf_kwargs["width"] = page_size[0]
                pdf_kwargs["height"] = page_size[1]
                pdf_kwargs["prefer_css_page_size"] = False

            page.pdf(**pdf_kwargs)
            browser.close()
    except PWError as e:
        raise RuntimeError(
            "Playwright/Chromium 실행 실패. pip install playwright && python -m playwright install chromium"
        ) from e
    finally:
        tmp_html.unlink(missing_ok=True)

# -----------------------------
# PDF 작성기 (WeasyPrint, 선택)
# -----------------------------
def write_pdf_with_weasyprint(
    html_str: str, base_url: Path, out_pdf: Path,
    page_size: Optional[Tuple[str, str]], margin: str
) -> None:
    try:
        from weasyprint import HTML, CSS
    except Exception:
        raise RuntimeError("WeasyPrint 실행 불가. Windows에선 --engine chromium 권장.")
    # WeasyPrint는 CSS @page를 읽으므로 별도 width/height 인자가 없음
    HTML(string=html_str, base_url=str(base_url)).write_pdf(
        target=str(out_pdf),
        stylesheets=[CSS(string="")],
        presentational_hints=True,
        optimize_size=("fonts", "images"),
        attachments=None,
        zoom=1.0,
        metadata=None,
    )

# -----------------------------
# 병합/분할
# -----------------------------
def merge_pdfs(pdf_paths: List[Path], out_pdf: Path) -> None:
    writer = PdfWriter()
    for p in pdf_paths:
        reader = PdfReader(str(p))
        for page in reader.pages:
            writer.add_page(page)
    with out_pdf.open("wb") as f:
        writer.write(f)
    print(f"[INFO] PDF 병합 완료: {out_pdf}")

def export_split_by_chapter(
    opf_path: Path,
    spine_hrefs: List[str],
    css_hrefs: List[str],
    out_dir: Path,
    engine: str,
    page_size: Optional[Tuple[str, str]],
    margin: str,
) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    extra_css = build_extra_css(page_size, margin)
    with tqdm(total=len(spine_hrefs), desc="챕터 변환 진행", unit="chap") as pbar:
        for i in range(len(spine_hrefs)):
            part_hrefs = [spine_hrefs[i]]
            html_str, base_url = build_single_html(opf_path, part_hrefs, css_hrefs, extra_css)
            out_pdf = out_dir / f"chapter_{i+1:04d}.pdf"
            if engine == "chromium":
                write_pdf_with_chromium(html_str, base_url, out_pdf, page_size, margin)
            else:
                write_pdf_with_weasyprint(html_str, base_url, out_pdf, page_size, margin)
            paths.append(out_pdf)
            pbar.update(1)
    return paths

# -----------------------------
# main
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="EPUB → 벡터 PDF 변환기")
    ap.add_argument("epub", type=str, help="입력 EPUB 경로")
    ap.add_argument("-o", "--output", type=str, default=None, help="출력 PDF 경로")
    ap.add_argument("--split", action="store_true", help="챕터별 PDF 생성 후 병합")
    ap.add_argument("--engine", choices=["chromium", "weasyprint"], default="chromium", help="PDF 엔진 선택")
    ap.add_argument("--page", type=str, default="oreilly",
                    help="페이지 크기 (예: a4, b5, a5, oreilly, 7x9in, 178x229mm, css)")
    ap.add_argument("--margin", type=str, default="0mm",
                    help="모든 방향 여백 (예: 0mm, 10mm, 0.5in)")
    args = ap.parse_args()

    epub_path = Path(args.epub).expanduser().resolve()
    if not epub_path.exists():
        raise FileNotFoundError(f"EPUB 파일 없음: {epub_path}")
    out_pdf = Path(args.output).resolve() if args.output else epub_path.with_suffix(".pdf")

    page_size = parse_page_arg(args.page)
    margin = normalize_margin(args.margin)

    print(f"[INFO] 입력 EPUB : {epub_path}")
    print(f"[INFO] 출력 PDF  : {out_pdf}")
    print(f"[INFO] 엔진      : {args.engine}")
    print(f"[INFO] 페이지    : {args.page} → {('CSS @page' if page_size is None else f'{page_size[0]} × {page_size[1]}')}")
    print(f"[INFO] 여백      : {args.margin}")
    print(f"[INFO] 분할 모드 : {'ON' if args.split else 'OFF'}")

    with tempfile.TemporaryDirectory(prefix="epub2pdf_") as td:
        tmp = Path(td)
        unzip_epub(epub_path, tmp)
        opf_path = find_opf(tmp)
        spine_hrefs, id_to_href, id_to_media = parse_opf(opf_path)
        css_hrefs = collect_css(id_to_href, id_to_media)

        extra_css = build_extra_css(page_size, margin)

        if args.split:
            part_dir = tmp / "parts"
            pdfs = export_split_by_chapter(
                opf_path, spine_hrefs, css_hrefs, part_dir,
                engine=args.engine, page_size=page_size, margin=margin
            )
            merge_pdfs(pdfs, out_pdf)
        else:
            html_str, base_url = build_single_html(opf_path, spine_hrefs, css_hrefs, extra_css)
            if args.engine == "chromium":
                write_pdf_with_chromium(html_str, base_url, out_pdf, page_size, margin)
            else:
                write_pdf_with_weasyprint(html_str, base_url, out_pdf, page_size, margin)

    print(f"[OK] PDF 생성 완료: {out_pdf}")

if __name__ == "__main__":
    main()
