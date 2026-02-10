from bs4 import BeautifulSoup

def extract_text_via_bs4(html: str) -> str:
    soup = BeautifulSoup(html)
    return soup.get_text(" ", strip=True)