# 기본

import os, json, time, importlib, threading
from ctypes import windll
from pathlib import Path
from functools import cache

# 설치

import pystray, pyperclip
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pynput import keyboard


################################################################################

# 이미지 관련


def _recolor_black_image(im, color):
    # 검은색 이미지를 다른 색으로 바꾸는 함수다. 참고: https://stackoverflow.com/a/6501902
    data = np.array(im.copy())
    red, green, blue = data[:, :, 0], data[:, :, 1], data[:, :, 2]
    mask = (red < 128) & (green < 128) & (blue < 128)
    data[:, :, :3][mask] = color
    new_im = Image.fromarray(data)
    return new_im


def _composite_letter(letter):
    # 이미지 위에 적당히 글씨를 쓰는 함수다. 참고: https://stackoverflow.com/a/1970930
    assert len(letter) == 1
    font = ImageFont.truetype("arial.ttf", 32)
    new_im = img_default.copy()
    draw = ImageDraw.Draw(new_im)
    _, _, w, h = draw.textbbox((0, 0), letter, font=font)
    draw.text((32 - w / 2, 34 - h / 2), letter, fill="black", font=font)
    return new_im


def _composite_image(image):
    # 이미지 위에 적당히 다른 이미지를 배치하는 함수다.
    im = Image.open(image)
    im.thumbnail((32, 32), Image.LANCZOS)
    new_im = img_default.copy()
    new_im.paste(im, (16, 18))
    return new_im


@cache
def get_modified_image(color, letter, image):
    # 모든 클립보드 아이콘은 이 함수로 만든다.
    assert not ((letter is not None) and (image is not None))
    if letter is not None:
        return _recolor_black_image(_composite_letter(letter), color)
    elif image is not None:
        return _recolor_black_image(_composite_image(image), color)
    else:
        return _recolor_black_image(img_default, color)


WHITE = (255, 255, 255)

################################################################################

# 클립보드 관련


def inclip_show():  # 알림으로 보여주기
    inclip_icon.remove_notification()
    inclip_icon.notify(pyperclip.paste()[:256])


def inclip_empty():  # 클립보드 비우기
    inclip_icon.remove_notification()
    pyperclip.copy("")


def inclip_halt():  # 프로그램 종료, 더 좋은 방법이 있나?
    inclip_icon.stop()
    global stop_listening
    stop_listening = True


def listen_for_clip():
    text = None
    while True:  # 무한 루프
        time.sleep(float(settings["sleep_time"]))
        try:
            new_text = pyperclip.paste()
            if new_text != text:  # 텍스트가 바뀌었으면
                text = new_text
                if text == "":  # 비었으면 더 이상 진행 X
                    inclip_icon.icon = get_modified_image(WHITE, "E", None)
                else:
                    if settings["alert_at_every_copy"]:
                        inclip_show()  # 복사할 때마다 보여주는 세팅인 경우
                    if settings["remove_format"]:
                        pyperclip.copy(text)  # 포맷 제거 (아마도?)

                    # 플러그인 순서대로 탐색
                    color, letter, image = WHITE, None, None
                    never_caught = True
                    for plugin in PLUGINS:
                        if plugin.caught(text):
                            if plugin.plugin_type == "color":
                                color = plugin.color
                            elif plugin.pluein_type == "letter":
                                image = None
                                letter = plugin.letter
                            elif plugin.plugin_type == "image":
                                letter = None
                                image = plugin.image
                            # 아이콘 업데이트
                            inclip_icon.icon = get_modified_image(color, letter, image)
                            never_caught = False
                    if never_caught:
                        # 클립보드의 텍스트가 '정상적'임
                        inclip_icon.icon = get_modified_image(WHITE, None, None)
            if stop_listening:
                break
        except pyperclip.PyperclipWindowsException:
            pass  # 유저가 노트북을 덮으면 이런 에러가 발생할 수 있음
        except:
            raise  # 심각한 문제


################################################################################

os.chdir(Path(__file__).parent.resolve())  # 기본 경로 설정
windll.shcore.SetProcessDpiAwareness(1)  # 트레이 메뉴 선명하게
img_default = Image.open("9040260_clipboard_icon.png")  # 기본 이미지
get_modified_image(WHITE, "E", None)  # 캐시

settings = json.loads(open("settings.json").read())  # 설정 읽기
cur_lang_data = json.loads(open("lang_data.json", encoding="u8").read())[
    settings["language"]
]

# 플러그인 로드
PLUGINS = [
    importlib.import_module("..main", "plugins." + pn + ".subpkg")
    for pn in settings["enabled_plugins"]
]

# 아이콘 생성
inclip_icon = pystray.Icon(
    "INCLIP",
    icon=get_modified_image(WHITE, None, None),
    menu=pystray.Menu(
        pystray.MenuItem(cur_lang_data["inclip_show"], inclip_show),
        pystray.MenuItem(cur_lang_data["inclip_empty"], inclip_empty),
        pystray.MenuItem(cur_lang_data["inclip_halt"], inclip_halt),
    ),
)

# 아이콘 바꾸는 스레드 생성
stop_listening = False
thread = threading.Thread(target=lambda: listen_for_clip())
thread.start()

# 단축키 듣기
hotkey = keyboard.GlobalHotKeys({"<alt>+z": inclip_show, "<alt>+x": inclip_empty})
hotkey.start()

# 시작
inclip_icon.run()
