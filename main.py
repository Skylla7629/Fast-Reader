## FastReader Main Module
import time

import bs4
import requests
from lxml import html

from tui import TUI


class FastReader:
    def __init__(self) -> None:
        self.webHandler = WebHandler()
        self.tui = TUI(self)
        self.running = True
        self.request = False
        self.request_type = None

        # Reader
        self.reading = False
        self.speed = 200  # ms
        self.multiplyer: float = 1.0
        self.current_word_index = 0
        self.current_paragraph_index = 0
        self.paused = False

    def run(self):
        self.tui.start()
        time.sleep(0.1)  # Give TUI time to initialize
        url = self.tui.getUserInput("Enter URL: ")
        if url:
            self.webHandler.parse(url)
            # Further processing can be done here

        while self.running:
            if self.webHandler.words:
                if self.reading:
                    self.tui.put_word(self.webHandler.words[self.current_word_index][0])
                    self.multiplyer = self.webHandler.words[self.current_word_index][1]
                    self.current_word_index += 1
                    self.current_paragraph_index = self.webHandler.words[
                        self.current_word_index
                    ][2]

                    if self.current_word_index >= len(self.webHandler.words):
                        self.pause()

            if self.request:
                if self.request_type == "URL":
                    url = self.tui.getUserInput("Enter URL: ")
                    if url:
                        self.webHandler.parse(url)
                self.request = False
                self.request_type = None

            time.sleep((self.speed / 1000) * self.multiplyer)

        self.tui.close()

    def dump(self):
        with open("dump.txt", "w") as f:
            f.write(f"Total words: {len(self.webHandler.words)}\n")
            f.write(f"Total paragraphs: {len(self.webHandler.paragraph_index)}\n")

            f.write("\nFull Text:\n")
            last = 0
            for word, speed, x in self.webHandler.words:
                if x != last:
                    f.write("\n")
                f.write(f"{word}")
                if speed != 1:
                    f.write(f"({speed}) ")
                else:
                    f.write(" ")
                last = x

            f.write("\n\nWord List:\n")
            for word, speed, x in self.webHandler.words:
                f.write(f"{word} ({speed})\n")

    def speed_up(self):
        self.speed -= 50

    def speed_down(self):
        self.speed += 50

    def p_back(self):
        self.current_paragraph_index = max(0, self.current_paragraph_index - 1)
        self.current_word_index = self.webHandler.paragraph_index[
            self.current_paragraph_index
        ]

    def p_forward(self):
        self.current_paragraph_index = min(
            len(self.webHandler.words) - 1, self.current_paragraph_index + 1
        )
        self.current_word_index = self.webHandler.paragraph_index[
            self.current_paragraph_index
        ]

    def pause(self, set=None):
        if set is not None:
            self.reading = set
        else:
            self.reading = not self.reading

    def stop(self):
        self.running = False

    def url_request(self):
        self.request = True
        self.request_type = "URL"


class WebHandler:
    def __init__(self) -> None:
        self.words: list[tuple[str, float, int]] = []
        self.paragraph_index: list[int] = []

    def parse(self, url: str) -> None:
        try:
            response = self.fetch_content(url)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL: {e}")
            return
        raw_words: list[list[str]] = self.extract_paragraph(response)

        # second step flatten all sentences into seperate segments
        buffer: list[tuple[str, float, int]] = []
        paragraph_index: list[int] = []
        for x, paragraph in enumerate(raw_words):
            paragraph_index.append(len(buffer))
            for i, word in enumerate(paragraph):
                if i == len(paragraph) - 1:
                    buffer.append((word, 3, x))
                elif word.endswith(","):
                    buffer.append((word, 2, x))
                elif word.endswith("."):
                    buffer.append((word, 2.5, x))
                elif len(word) > 10:
                    buffer.append((word, 1.7, x))
                else:
                    buffer.append((word, 1, x))
        self.words = buffer
        self.paragraph_index = paragraph_index

        # print(self.words)

    def fetch_content(self, url: str) -> requests.Response:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        response = requests.get(url, timeout=2, headers=headers)
        return response

    def extract_paragraph(self, response: requests.Response) -> list:
        tree = html.fromstring(response.content)
        paragraphs = tree.xpath('//*[@id="chr-content"]')
        if not paragraphs:
            return []
        soup = bs4.BeautifulSoup(html.tostring(paragraphs[0]), "html.parser")
        paragraphs = soup.find_all("p")
        words = []
        for p in paragraphs:
            words += [p.get_text(strip=False).split(" ")]
        return words


def main():
    # wHandler = WebHandler()
    # url = "https://novelbin.com/b/dual-cultivation-novel/chapter-1"
    # content = wHandler.extract_paragraph(wHandler.fetch_content(url))
    # print(content)

    fastReader = FastReader()
    fastReader.run()


if __name__ == "__main__":
    main()
