## FastReader Main Module
import requests
from lxml import html
import bs4

class Display:
    def __init__(self) -> None:
        pass



class WebHandler:
    def __init__(self) -> None:
        pass
    
    def fetch_content(self, url: str) -> requests.Response:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        response = requests.get(url, timeout=2, headers=headers)
        return response

    def extract_paragraph(self, response: requests.Response) -> list:
        tree = html.fromstring(response.content)
        paragraphs = tree.xpath('//*[@id="chr-content"]')
        soup = bs4.BeautifulSoup(html.tostring(paragraphs[0]), 'html.parser')
        paragraphs = soup.find_all('p')
        words = []
        for p in paragraphs:
            words += [p.get_text(strip=False).split(" ")]
        return words


def main():
    wHandler = WebHandler()
    url = "https://novelbin.com/b/dual-cultivation-novel/chapter-1"
    content = wHandler.extract_paragraph(wHandler.fetch_content(url))
    print(content)


if __name__ == "__main__":
    main()
