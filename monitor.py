# monitor.py (들여쓰기 수정 및 피드백 강화 최종 버전)

# --- 1. 기본 도구 불러오기 ---
import requests
import pandas as pd
from datetime import datetime, timedelta
import sys
import time
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# --- 2. 사용자 설정 (이 부분은 GitHub Secrets를 통해 자동으로 채워집니다) ---
API_KEY = os.environ.get("GNEWS_API_KEY")
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

SEARCH_KEYWORDS = [
    "Lee Jae-yong", "Samsung Electronics",
    "Chey Tae-won", "SK Hynix",
    "Euisun Chung", "Hyundai Motor",
    "Koo Kwang-mo", "LG Corp",
    "Shin Dong-bin", "Lotte"
]

# --- 3. 실제 프로그램 작동 부분 (여기는 수정하지 마세요!) ---

def get_news():
    """뉴스 API를 호출해서 관련 기사를 가져오는 함수"""
    print("해외 뉴스 검색을 시작합니다...")
    all_articles = []
    today = datetime.now()
    start_date = today - timedelta(days=1)
    start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    for keyword in SEARCH_KEYWORDS:
        print(f"\n▶ '{keyword}' 키워드로 검색 중...")
        query = f'"{keyword}"'
        url = (f"https://gnews.io/api/v4/search?q={query}"
               f"&lang=en&max=10&from={start_date_str}"
               f"&sortby=publishedAt&token={API_KEY}")

        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"  [오류] 서버 응답 오류 (상태 코드: {response.status_code})")
                continue
            data = response.json()
            articles = data.get('articles', [])
            if not articles:
                print(f"  [결과] '{keyword}'에 대한 기사를 찾지 못했습니다.")
                continue
            print(f"  [성공] {len(articles)}개의 기사를 찾았습니다.")
            for article in articles:
                all_articles.append({
                    "총수 이름/기업명": keyword, "보도 날짜": article.get('publishedAt', '').split('T')[0],
                    "매체명": article.get('source', {}).get('name', ''), "기사 제목": article.get('title', ''),
                    "기사 요약": article.get('description', ''), "원본 링크": article.get('url', '')
                })
        except Exception as e:
            print(f"  [오류] 검색 중 문제 발생: {e}")
        time.sleep(1)
            
    print(f"\n총 {len(all_articles)}개의 유효한 기사를 찾았습니다.")
    return all_articles

def save_to_excel(articles):
    """뉴스 기사 목록을 엑셀 파일로 저장하는 함수"""
    if not articles:
        return None
    df = pd.DataFrame(articles)
    if df.empty: return None
    df = df.drop_duplicates(subset=['기사 제목', '원본 링크'])
    if df.empty:
        return None
        
    filename = f"news_monitoring_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"'{filename}' 파일이 임시 저장되었습니다.")
    return filename

def send_email(filename, articles_found):
    """결과를 이메일로 발송하는 함수"""
    print("\n이메일 발송을 준비합니다...")
    
    # 이메일 서버 설정
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    
    # 이메일 내용 구성
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_ADDRESS

    if articles_found:
        # 기사가 있을 경우
        msg["Subject"] = f"[{datetime.now().strftime('%Y-%m-%d')}] 해외 언론 모니터링 결과 (기사 발견)"
        body = MIMEText("오늘의 해외 언론 모니터링 결과를 엑셀 파일로 첨부합니다.", "plain")
        msg.attach(body)
        
        # 파일 첨부
        if filename:
            try:
                with open(filename, "rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(filename))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(filename)}"'
                msg.attach(part)
                print(f"'{filename}' 파일을 성공적으로 첨부했습니다.")
            except FileNotFoundError:
                print(f"[오류] 첨부할 파일 '{filename}'을 찾을 수 없습니다.")
                return # 파일이 없으면 이메일 발송 중단
    else:
        # 기사가 없을 경우
        msg["Subject"] = f"[{datetime.now().strftime('%Y-%m-%d')}] 해외 언론 모니터링 시스템 정상 작동 알림"
        body_text = "오늘 모니터링 결과, 지정된 키워드에 대한 새로운 해외 기사를 찾지 못했습니다.\n시스템은 정상적으로 작동 중입니다."
        body = MIMEText(body_text, "plain")
        msg.attach(body)
        print("기사가 없어 확인 이메일을 준비합니다.")

    # 이메일 발송
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print("이메일 서버에 연결 중...")
            server.starttls()
            print("서버와 보안 연결 시작...")
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            print("로그인 성공. 이메일을 발송합니다...")
            server.send_message(msg)
            print("🎉 이메일 발송 성공!")
    except Exception as e:
        print(f"[치명적 오류] 이메일 발송에 실패했습니다: {e}")
    finally:
        # 이메일 발송 후 임시 엑셀 파일 삭제
        if filename and os.path.exists(filename):
            os.remove(filename)
            print(f"임시 파일 '{filename}'을 삭제했습니다.")

# --- 프로그램 실행 ---
if __name__ == "__main__":
    # 프로그램 시작 시 정보 확인
    if "YOUR_GNEWS" in API_KEY or not API_KEY or \
       "your_email" in GMAIL_ADDRESS or not GMAIL_ADDRESS or \
       "your_gmail" in GMAIL_APP_PASSWORD or not GMAIL_APP_PASSWORD:
        print("!!! 중요: API 키 또는 이메일 정보가 설정되지 않았습니다.")
        print("monitor.py 파일 상단의 API_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD 변수를 확인해주세요.")
        sys.exit()

    news_list = get_news()
    
    if news_list:
        excel_file = save_to_excel(news_list)
        send_email(excel_file, articles_found=True)
    else:
        # 기사가 없어도 이메일을 보내서 시스템이 작동했음을 알림
        send_email(None, articles_found=False)
