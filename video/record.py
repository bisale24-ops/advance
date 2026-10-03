"""Record the demo clips from the running page: real requests, real Qloo answers.

    PORT=8792 ~/.venvs/video/bin/python video/record.py      # writes video/clips/*.webm
"""
import os
import pathlib
import shutil

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
OUT = HERE / "clips"
URL = f"http://127.0.0.1:{os.environ.get('PORT', '8792')}/"
ASKS = [("phoebe", "Phoebe Bridgers in Chicago, US"), ("metallica", "Metallica in Berlin and Munich, Germany")]


def scroll(page, total, step=6, pause=16):
    for _ in range(total // step):
        page.mouse.wheel(0, step)
        page.wait_for_timeout(pause)


def clip(browser, name, act):
    tmp = OUT / f"_{name}"
    shutil.rmtree(tmp, ignore_errors=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=str(tmp),
                              record_video_size={"width": 1280, "height": 720}, color_scheme="light")
    page = ctx.new_page()
    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(700)
    act(page)
    video = page.video
    ctx.close()
    pathlib.Path(video.path()).replace(OUT / f"{name}.webm")
    shutil.rmtree(tmp, ignore_errors=True)
    print(name, flush=True)


def ask(text):
    def act(page):
        page.click("#text")
        page.type("#text", text, delay=40)
        page.wait_for_timeout(300)
        page.click("#go")
        page.wait_for_selector(".grid .card", timeout=120000)
        page.wait_for_timeout(1500)
        scroll(page, 420)
        page.wait_for_timeout(2500)
        scroll(page, 900)
        page.wait_for_timeout(2500)
        scroll(page, 900)
        page.wait_for_timeout(2000)
    return act


def proof(page):
    page.evaluate("document.getElementById('proof').scrollIntoView({block: 'center'})")
    page.wait_for_timeout(9000)


def main():
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, text in ASKS:
            clip(browser, name, ask(text))
        clip(browser, "proof", proof)
        browser.close()


if __name__ == "__main__":
    main()
