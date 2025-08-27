# oreillyBook

[_Oreilly Books Online_](https://www.oreilly.com/) 라이브러리에서 원하는 책을 다운로드하여 _EPUB_ 형태로 생성합니다.
이 프로그램의 사용에 대한 책임은 사용자에게 있으며, 본 도구는 *개인적*이고 _교육적_ 목적에 한합니다.
사용 전에 반드시 *O'Reilly*의 [이용 약관](https://learning.oreilly.com/terms/)을 읽어주세요.

## 추가 기능
1. Epub -> PDF 스크립트추가
2. Font 다운로드 로직추가

## _확인 필요_
- [lorenzodifuccia/safaribooks](https://github.com/lorenzodifuccia/safaribooks.git)을 통해서 수정하였습니다.
- ORLY API 변경으로 인해 `safaribooks`를 통한 *로그인*이 더 이상 동작하지 않습니다.
- 새 기능 추가와 신규 API 통합을 위해 대대적인 리팩터링이 필요합니다.
- **하지만… 여전히 책 다운로드는 가능합니다.**
  (SSO 해킹(?) 우회: 브라우저로 로그인한 뒤 쿠키를 `cookies.json`에 복사해 사용가능합니다.)

---

## 개요(Overview)

- [요구사항 & 설정](#요구사항 & 설정)
- [사용법](#사용법)
- [Single Sign-On (SSO), 기업/대학 로그인](https://github.com/lorenzodifuccia/safaribooks/issues/150#issuecomment-555423085)
- [PDF -> EPUB 변환](#EPUB → 벡터 PDF 변환기)

## 요구사항 & 설정

먼저 `python3`와 `pip3`가 설치되어 있어야 합니다.

```shell
$ git clone https://github.com/Seongho-haru/oreillybooks.git
Cloning into 'oreillybooks'...

$ conda create --name ebook python=3.13 -y
$ conda activate ebook

$ cd oreillybooks/
$ pip3 install -r requirements.txt
$ python -m playwright install chromium

```

프로그램은 **Python _3_** 모듈 여섯 개에만 의존합니다:

```python3
lxml>=4.1.1          # HTML/XML 파싱
requests>=2.20.0     # HTTP 요청
beautifulsoup4>=4.9  # HTML 파싱 (선택적으로 lxml 파서와 함께 사용)
pypdf>=3.0.0         # PDF 읽기/쓰기
playwright>=1.30.0   # 브라우저 자동화
tqdm>=4.60.0         # 진행률 표시
```

## 사용법

사용법은 매우 간단합니다. 라이브러리에서 책을 하나 고른 뒤, 아래 명령에서

- URL의 X 자리에는 책의 ID를,
- `email:password`는 본인 계정 정보를
  넣어 실행하세요.

```shell
$ python3 safaribooks.py XXXXXXXXXXXXX
```

책의 ID는 해당 책 설명 페이지의 URL에서 찾을 수 있는 숫자 부분입니다:
`https://learning.oreilly.com/library/view/mitbadagbuteo-sijaghaneun-dibreoning/XXXXXXXXXXXXX/`

예: `https://learning.oreilly.com/library/view/mitbadagbuteo-sijaghaneun-dibreoning/9788968484636/`

#### 프로그램 옵션

```shell
$ python3 safaribooks.py --help
usage: safaribooks.py [--cred <EMAIL:PASS> | --login] [--no-cookies]
                      [--kindle] [--preserve-log] [--help]
                      <BOOK ID>

Safari Books Online에서 원하는 책을 EPUB 형식으로 다운로드하고 생성합니다.

positional arguments:
  <BOOK ID>           다운로드하려는 책의 ID 숫자입니다.
                      책 URL의 X 표시 부분에서 찾을 수 있습니다:
                      https://learning.oreilly.com/library/view/book-name/XXXXXXXXXXXXX/

optional arguments:
  --cred <EMAIL:PASS>  Safari Books Online 로그인에 사용할 계정 정보. 예: ` --cred
                       "account_mail@mail.com:password01" `.

  --login              Safari Books Online 로그인 시 프롬프트에서 계정 정보를
                       입력받음.

  --no-cookies         세션 데이터를 `cookies.json` 파일에 저장하지 않음.

  --kindle             EPUB을 아마존 킨들과 같은 전자책 리더기로 내보낼 때 `table`,
                       `pre` 요소의 넘침(overflow)을 막는 CSS 규칙을 추가.

  --preserve-log       오류가 없어도 `info_XXXXXXXXXXXXX.log` 파일을 남김.

  --help               도움말 메시지를 표시.

```

처음 사용할 때는 Safari Books Online 계정 자격 증명을 제공해야 합니다([특수문자 관련 참고](../../issues/15)).
세션이 만료되기 전까지는 이후 다운로드에서 자격 증명을 생략할 수 있습니다. 프로그램이 세션 쿠키를 `cookies.json` 파일에 저장하기 때문입니다.
**SSO**를 사용하는 경우, 브라우저에서 가져온 SSO 쿠키로 `cookies.json`을 만드는 `sso_cookies.py`를 사용하세요(설명은 [`여기`](../../issues/150#issuecomment-555423085) 참고).

공용/공유 PC를 사용하는 경우 주의하세요. 해당 파일에 접근 가능한 사람은 세션을 탈취할 수 있습니다.
쿠키 캐시를 원치 않는다면 `--no-cookies` 옵션을 사용하고, 매번 `--cred` 또는 더 안전한 `--login` 옵션으로 자격 증명을 입력하세요. `--login`은 실행 중에 프롬프트로 입력받습니다.

프록시가 필요하면 시스템 환경 변수 `HTTPS_PROXY`를 설정하거나, 스크립트 내 `USE_PROXY` 지시어를 사용해 구성할 수 있습니다.

# EPUB → 벡터 PDF 변환기

**중요** : 이 스크립트는 HTML 페이지를 내려받아 ‘가공되지 않은’ EPUB을 생성합니다. 따라서 많은 CSS 와 Font 및 XML/HTML 지시문이 일반 전자책 리더에는 맞지 않을 수 있습니다. 최상의 출력 품질을 위해, 생성한 `EPUB`을 PDF로 변환하는 스크립트를 추가했습니다

EPUB 전자책을 **벡터 기반 PDF**로 변환합니다.
기본적으로 **Chromium** 기반으로 동작하며, 페이지 크기와 여백을 지정할 수 있습니다.

---

## 사용 방법

```bash
python epub2pdf.py <EPUB 경로> [옵션...]
```

**예시:**

```bash
python epub2pdf.py mybook.epub -o mybook.pdf --page a4 --margin 10mm
```

---

## 옵션 설명

| 옵션           | 기본값             | 설명                                                                                                           |
| -------------- | ------------------ | -------------------------------------------------------------------------------------------------------------- |
| `epub`         | (필수)             | 입력 EPUB 파일 경로                                                                                            |
| `-o, --output` | `<입력파일명>.pdf` | 출력 PDF 경로                                                                                                  |
| `--split`      | 없음               | 챕터별 PDF 생성 후 병합 (대용량 EPUB 권장)                                                                     |
| `--engine`     | `chromium`         | PDF 엔진 선택: `chromium`, `weasyprint`                                                                        |
| `--page`       | `oreilly`          | 페이지 크기 지정:<br>• **a4, b5, a5, oreilly(7x9in)**<br>• 사용자 정의: `178x229mm`<br>• CSS @page 사용: `css` |
| `--margin`     | `0mm`              | 페이지 여백 (예: `10mm`, `0.5in`, `12px`)                                                                      |

---

## 페이지 크기 프리셋

| 이름      | 크기        |
| --------- | ----------- |
| `a4`      | 210 × 297mm |
| `letter`  | 8.5 × 11in  |
| `a5`      | 148 × 210mm |
| `b5`      | 176 × 250mm |
| `oreilly` | 7 × 9in     |

사용자 정의 크기:

```
--page 178x229mm
```

---

## 실행 예시

1. **기본 변환 (O'Reilly 규격, 여백 없음)**

```bash
python epub2pdf.py mybook.epub
```

2. **A4, 여백 10mm, 출력 파일 지정**

```bash
python epub2pdf.py mybook.epub -o output.pdf --page a4 --margin 10mm
```

3. **챕터별 분할 후 병합 (대용량 EPUB 안정성 ↑)**

```bash
python epub2pdf.py mybook.epub --split
```

---

## 감사합니다(Thanks!!)

문제가 생기면 언제든 _GitHub_ 이슈로 알려주세요.

## 원본(Fork)

[원본 Fork](https://github.com/lorenzodifuccia/safaribooks)



