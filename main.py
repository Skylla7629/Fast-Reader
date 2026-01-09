## FastReader Main Module
import requests
from lxml import html
import bs4
from tui import TUI
import time


class FastReader:
    def __init__(self) -> None:
        self.webHandler = WebHandler()
        self.tui = TUI(self)
        self.running = True
        self.request = False
        self.request_type = None

    def run(self):
        self.tui.start()
        time.sleep(0.1)  # Give TUI time to initialize
        url = self.tui.getUserInput("Enter URL: ")
        if url:
            self.webHandler.parse(url)
            # Further processing can be done here

        while self.running:
            if self.request:
                if self.request_type == "URL":
                    url = self.tui.getUserInput("Enter URL: ")
                    if url:
                        self.webHandler.parse(url)
                self.request = False
                self.request_type = None
            time.sleep(0.1)

        self.tui.close()

    def stop(self):
        self.running = False

    def url_request(self):
        self.request = True
        self.request_type = "URL"


class WebHandler:
    def __init__(self) -> None:
        self.words = []

    def parse(self, url: str) -> None:
        try:
            response = self.fetch_content(url)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL: {e}")
            return
        self.words = self.extract_paragraph(response)
        print(self.words)

    def fetch_content(self, url: str) -> requests.Response:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        response = requests.get(url, timeout=2, headers=headers)
        return response

    def extract_paragraph(self, response: requests.Response) -> list:
        tree = html.fromstring(response.content)
        paragraphs = tree.xpath('//*[@id="chr-content"]')
        if not paragraphs:
            return []
        soup = bs4.BeautifulSoup(html.tostring(paragraphs[0]), 'html.parser')
        paragraphs = soup.find_all('p')
        words = []
        for p in paragraphs:
            words += [p.get_text(strip=False).split(" ")]
        return words


def main():
    #wHandler = WebHandler()
    #url = "https://novelbin.com/b/dual-cultivation-novel/chapter-1"
    #content = wHandler.extract_paragraph(wHandler.fetch_content(url))
    #print(content)

    fastReader = FastReader()
    fastReader.run()


if __name__ == "__main__":
    main()
