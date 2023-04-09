plugin_type = "color"
color = (255, 0, 0)


def caught(text):
    range_list = [
        [10, 13],
        range(32, 127),
        range(0xAC00, 0xD7A4),
    ]
    return not all(any(ord(letter) in r for r in range_list) for letter in text)
