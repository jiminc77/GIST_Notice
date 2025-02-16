#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import os
import re
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText

# --------------------------------------------------------
# 환경 변수 (GitHub Actions → Secrets)로 받는 값들
# --------------------------------------------------------
# 아래 값들은 코드 내에서 os.environ[...]로 가져올 예정
# GIST_ID            : Gist 식별자 (gist.github.com/.../... 중 뒤쪽)
# GIST_TOKEN         : Gist 접근용 Personal Access Token (repo→public_gist 권한 필요)
# SMTP_SERVER        : SMTP 서버 (예: smtp.gmail.com)
# SMTP_PORT          : SMTP 포트 (예: 587)
# SMTP_USERNAME      : SMTP 계정 (예: your_gmail@gmail.com)
# SMTP_PASSWORD      : SMTP 비밀번호 (앱 비밀번호)
# MAIL_SENDER        : 발신 메일 주소
# MAIL_RECEIVER      : 수신 메일 주소

# --------------------------------------------------------
# 1. GIST 학사공지 페이지
# --------------------------------------------------------

NOTICE_URL = "https://www.gist.ac.kr/kr/html/sub05/050209.html?mode=L"


# --------------------------------------------------------
# 2. Gist에서 last_id.txt 가져오기 / 저장하기
# --------------------------------------------------------

def get_last_id_from_gist(gist_id: str, token: str) -> int:
    """
    Gist의 last_id.txt 파일을 가져와서 정수 변환, 없거나 실패하면 -1
    """
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print("Failed to GET Gist:", resp.text)
        return -1
    
    data = resp.json()
    files = data.get("files", {})
    file_info = files.get("last_id.txt", None)
    if not file_info:
        return -1  # 파일이 없으면 -1
    
    content = file_info.get("content", "").strip()
    try:
        return int(content)
    except ValueError:
        return -1


def save_last_id_to_gist(gist_id: str, token: str, new_id: int):
    """
    Gist의 last_id.txt 파일을 새 값으로 업데이트
    """
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "files": {
            "last_id.txt": {
                "content": str(new_id)
            }
        }
    }
    resp = requests.patch(url, headers=headers, json=payload)
    if resp.status_code not in [200, 201]:
        print("Failed to PATCH Gist:", resp.text)


# --------------------------------------------------------
# 3. GIST 학사공지 크롤링
# --------------------------------------------------------

def fetch_gist_notices():
    resp = requests.get(NOTICE_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tbody = soup.select_one("div.bd_list_wrap table tbody")
    if not tbody:
        return []
    
    rows = tbody.select("tr")
    notices = []
    for row in rows:
        row_id = row.get("id", "")
        m = re.match(r"BBSList(\d+)", row_id)
        if not m:
            continue
        post_id = int(m.group(1))
        
        td_title = row.select_one("td.title a")
        if not td_title:
            continue
        
        title_text = td_title.get_text(strip=True)
        link_href = td_title.get("href", "").strip()
        
        td_regdate = row.select_one("td.reg_date")
        date_text = td_regdate.get_text(strip=True) if td_regdate else ""
        
        notices.append({
            "post_id": post_id,
            "title": title_text,
            "link": link_href,
            "date": date_text
        })
    return notices


# --------------------------------------------------------
# 4. 이메일 발송
# --------------------------------------------------------

def send_email(subject, body, smtp_info):
    """
    smtp_info: {
      "server": ...,
      "port": ...,
      "user": ...,
      "password": ...,
      "sender": ...,
      "receiver": ...
    }
    """
    msg = MIMEText(body, _charset="utf-8")
    msg['Subject'] = subject
    msg['From'] = smtp_info["sender"]
    msg['To'] = smtp_info["receiver"]
    
    with smtplib.SMTP(smtp_info["server"], smtp_info["port"]) as server:
        server.starttls()
        server.login(smtp_info["user"], smtp_info["password"])
        server.sendmail(smtp_info["sender"], [smtp_info["receiver"]], msg.as_string())


# --------------------------------------------------------
# 5. 메인 로직
# --------------------------------------------------------

def main():
    # (1) 환경 변수에서 값 읽기
    gist_id = os.environ["GIST_ID"]
    gist_token = os.environ["GIST_TOKEN"]
    
    smtp_info = {
        "server": os.environ["SMTP_SERVER"],
        "port": int(os.environ["SMTP_PORT"]),
        "user": os.environ["SMTP_USERNAME"],
        "password": os.environ["SMTP_PASSWORD"],
        "sender": os.environ["MAIL_SENDER"],
        "receiver": os.environ["MAIL_RECEIVER"],
    }
    
    # (2) 현재 Gist에 저장된 last_id 불러오기
    last_id = get_last_id_from_gist(gist_id, gist_token)
    
    # (3) 학사공지 목록 크롤링
    notices = fetch_gist_notices()
    if not notices:
        print("No notices found.")
        return
    
    # (4) post_id 내림차순 정렬
    notices_sorted = sorted(notices, key=lambda x: x["post_id"], reverse=True)
    
    # (5) new_posts: last_id보다 큰 애들만
    new_posts = [n for n in notices_sorted if n["post_id"] > last_id]
    if not new_posts:
        print("No new posts.")
        return
    
    # (6) 가장 최신 ID 기록
    latest_id = new_posts[0]["post_id"]
    save_last_id_to_gist(gist_id, gist_token, latest_id)
    
    # (7) 이메일 본문
    lines = []
    for post in new_posts:
        full_link = f"https://www.gist.ac.kr/kr/html/sub05/050209.html{post['link']}"
        lines.append(
            f"- ID: {post['post_id']}\n"
            f"  제목: {post['title']}\n"
            f"  작성일: {post['date']}\n"
            f"  링크: {full_link}\n"
        )
    
    body = "새로운 학사공지 게시글이 등록되었습니다.\n\n" + "\n".join(lines)
    subject = f"[GIST 학사공지 알림] 새 글 {len(new_posts)}개"
    
    # (8) 이메일 전송
    send_email(subject, body, smtp_info)
    print(f"Sent email. New posts: {len(new_posts)}")


if __name__ == "__main__":
    main()
