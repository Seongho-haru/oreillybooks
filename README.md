# SafariBooks

[_Safari Books Online_](https://www.safaribooksonline.com) 라이브러리에서 원하는 책을 다운로드하여 _EPUB_ 형태로 생성합니다.
이 프로그램의 사용에 대한 책임은 사용자에게 있으며, 본 도구는 *개인적*이고 _교육적_ 목적에 한합니다.
사용 전에 반드시 *O'Reilly*의 [이용 약관](https://learning.oreilly.com/terms/)을 읽어주세요.

<a href='https://ko-fi.com/Y8Y0MPEGU' target='_blank'><img height='60' style='border:0px;height:60px;' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com'/></a>

## ✨✨ _확인 필요_ ✨✨

- 이 프로젝트는 더 이상 적극적으로 유지보수되지 않습니다.
- ORLY API 변경으로 인해 `safaribooks`를 통한 *로그인*이 더 이상 동작하지 않습니다.
- 새 기능 추가와 신규 API 통합을 위해 대대적인 리팩터링이 필요합니다.
- **하지만… 여전히 책 다운로드는 가능합니다.**
  (SSO 해킹(?) 우회: 브라우저로 로그인한 뒤 쿠키를 `cookies.json`에 복사해 사용 — 아래와 이슈들을 참고하세요. Love ❤️)

---

## 개요(Overview)

- [요구사항 & 설정](#requirements--setup)
- [사용법](#usage)
- [Single Sign-On (SSO), 기업/대학 로그인](https://github.com/lorenzodifuccia/safaribooks/issues/150#issuecomment-555423085)
- [Calibre EPUB 변환](https://github.com/lorenzodifuccia/safaribooks#calibre-epub-conversion)
- [예시: _Test-Driven Development with Python, 2nd Edition_ 다운로드](#download-test-driven-development-with-python-2nd-edition)
- [예시: `--kindle` 옵션 사용 여부](#use-or-not-the---kindle-option)

## Requirements & Setup

먼저 `python3`와 `pip3` 또는 `pipenv`가 설치되어 있어야 합니다.

```shell
$ git clone https://github.com/lorenzodifuccia/safaribooks.git
Cloning into 'safaribooks'...

$ cd safaribooks/
$ pip3 install -r requirements.txt

OR

$ pipenv install && pipenv shell
```

프로그램은 **Python _3_** 모듈 두 개에만 의존합니다:

```python3
lxml>=4.1.1
requests>=2.20.0
```

## 사용법

사용법은 매우 간단합니다. 라이브러리에서 책을 하나 고른 뒤, 아래 명령에서

- URL의 X 자리에는 책의 ID를,
- `email:password`는 본인 계정 정보를
  넣어 실행하세요.

```shell
$ python3 safaribooks.py --cred "account_mail@mail.com:password01" XXXXXXXXXXXXX
```

책의 ID는 해당 책 설명 페이지의 URL에서 찾을 수 있는 숫자 부분입니다:
`https://www.safaribooksonline.com/library/view/book-name/XXXXXXXXXXXXX/`
예: `https://www.safaribooksonline.com/library/view/test-driven-development-with/9781491958698/`

#### 프로그램 옵션

```shell
$ python3 safaribooks.py --help
usage: safaribooks.py [--cred <EMAIL:PASS> | --login] [--no-cookies]
                      [--kindle] [--preserve-log] [--help]
                      <BOOK ID>

Download and generate an EPUB of your favorite books from Safari Books Online.

positional arguments:
  <BOOK ID>            Book digits ID that you want to download. You can find
                       it in the URL (X-es):
                       `https://learning.oreilly.com/library/view/book-
                       name/XXXXXXXXXXXXX/`

optional arguments:
  --cred <EMAIL:PASS>  Credentials used to perform the auth login on Safari
                       Books Online. Es. ` --cred
                       "account_mail@mail.com:password01" `.
  --login              Prompt for credentials used to perform the auth login
                       on Safari Books Online.
  --no-cookies         Prevent your session data to be saved into
                       `cookies.json` file.
  --kindle             Add some CSS rules that block overflow on `table` and
                       `pre` elements. Use this option if you're going to
                       export the EPUB to E-Readers like Amazon Kindle.
  --preserve-log       Leave the `info_XXXXXXXXXXXXX.log` file even if there
                       isn't any error.
  --help               Show this help message.
```

처음 사용할 때는 Safari Books Online 계정 자격 증명을 제공해야 합니다([특수문자 관련 참고](../../issues/15)).
세션이 만료되기 전까지는 이후 다운로드에서 자격 증명을 생략할 수 있습니다. 프로그램이 세션 쿠키를 `cookies.json` 파일에 저장하기 때문입니다.
**SSO**를 사용하는 경우, 브라우저에서 가져온 SSO 쿠키로 `cookies.json`을 만드는 `sso_cookies.py`를 사용하세요(설명은 [`여기`](../../issues/150#issuecomment-555423085) 참고).

공용/공유 PC를 사용하는 경우 주의하세요. 해당 파일에 접근 가능한 사람은 세션을 탈취할 수 있습니다.
쿠키 캐시를 원치 않는다면 `--no-cookies` 옵션을 사용하고, 매번 `--cred` 또는 더 안전한 `--login` 옵션으로 자격 증명을 입력하세요. `--login`은 실행 중에 프롬프트로 입력받습니다.

프록시가 필요하면 시스템 환경 변수 `HTTPS_PROXY`를 설정하거나, 스크립트 내 `USE_PROXY` 지시어를 사용해 구성할 수 있습니다.

#### Calibre EPUB 변환

**중요**: 이 스크립트는 HTML 페이지를 내려받아 ‘가공되지 않은’ EPUB을 생성합니다. 따라서 많은 CSS 및 XML/HTML 지시문이 일반 전자책 리더에는 맞지 않을 수 있습니다. 최상의 출력 품질을 위해, 생성한 `EPUB`을 [Calibre](https://calibre-ebook.com/)로 표준 `EPUB`으로 변환하는 것을 권장합니다.
CLI 버전인 `ebook-convert`도 사용할 수 있어요:

```bash
$ ebook-convert "XXXX/safaribooks/Books/Test-Driven Development with Python 2nd Edition (9781491958698)/9781491958698.epub" "XXXX/safaribooks/Books/Test-Driven Development with Python 2nd Edition (9781491958698)/9781491958698_CLEAR.epub"
```

변환이 끝나면 `9781491958698_CLEAR.epub` 파일은 모든 e-리더에서 잘 열리며, 나머지 파일은 삭제해도 됩니다.

전자책 리더(예: Amazon Kindle)로 내보낼 호환성을 높이는 옵션 `--kindle`도 있습니다. `table`과 `pre` 요소의 overflow를 막습니다([예시](#use-or-not-the---kindle-option) 참고).
이 경우 Calibre로 `AZW3` 또는 `MOBI`로 변환하는 것을 권장합니다. `MOBI` 변환 시에는 변환 옵션에서 `Ignore margins(여백 무시)`를 선택하세요:

![Calibre IgnoreMargins](https://github.com/lorenzodifuccia/cloudflare/raw/master/Images/safaribooks/safaribooks_calibre_IgnoreMargins.png "Select Ignore margins")

## 예시(Examples)

- ## [Test-Driven Development with Python, 2nd Edition](https://www.safaribooksonline.com/library/view/test-driven-development-with/9781491958698/) 다운로드

  ```shell
  $ python3 safaribooks.py --cred "my_email@gmail.com:MyPassword1!" 9781491958698

         ____     ___         _
        / __/__ _/ _/__ _____(_)
       _\ \/ _ `/ _/ _ `/ __/ /
      /___/\_,_/_/ \_,_/_/ /_/
        / _ )___  ___  / /__ ___
       / _  / _ \/ _ \/  '_/(_-<
      /____/\___/\___/_/\_\/___/

  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  [-] Logging into Safari Books Online...
  [*] Retrieving book info...
  [-] Title: Test-Driven Development with Python, 2nd Edition
  [-] Authors: Harry J.W. Percival
  [-] Identifier: 9781491958698
  [-] ISBN: 9781491958704
  [-] Publishers: O'Reilly Media, Inc.
  [-] Rights: Copyright © O'Reilly Media, Inc.
  [-] Description: ...(중략)
  [-] Release Date: 2017-08-18
  [-] URL: https://learning.oreilly.com/library/view/test-driven-development-with/9781491958698/
  [*] Retrieving book chapters...
  [*] Output directory:
      /XXXX/safaribooks/Books/Test-Driven Development with Python 2nd Edition (9781491958698)
  [-] Downloading book contents... (53 chapters)
      [#####################################################################] 100%
  [-] Downloading book CSSs... (2 files)
      [#####################################################################] 100%
  [-] Downloading book images... (142 files)
      [#####################################################################] 100%
  [-] Creating EPUB file...
  [*] Done: /XXXX/safaribooks/Books/Test-Driven Development with Python 2nd Edition
  (9781491958698)/9781491958698.epub

      If you like it, please * this project on GitHub to make it known:
          https://github.com/lorenzodifuccia/safaribooks
      e don't forget to renew your Safari Books Online subscription:
          https://learning.oreilly.com

  [!] Bye!!
  ```

  결과(생성된 `EPUB`을 Calibre로 열었을 때)는 다음과 같습니다:

  ![Book Appearance](https://github.com/lorenzodifuccia/cloudflare/raw/master/Images/safaribooks/safaribooks_example01_TDD.png "Book opened with Calibre")

- ## `--kindle` 옵션 사용 여부

  ```bash
  $ python3 safaribooks.py --kindle 9781491958698
  ```

  오른쪽이 `--kindle` 옵션을 사용해 만든 버전, 왼쪽이 기본(옵션 미사용) 버전입니다:

  ![NoKindle Option](https://github.com/lorenzodifuccia/cloudflare/raw/master/Images/safaribooks/safaribooks_example02_NoKindle.png "Version compare")

---

## 감사합니다(Thanks!!)

문제가 생기면 언제든 _GitHub_ 이슈로 알려주세요.

_Lorenzo Di Fuccia_
