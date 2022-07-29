import re


def pretty_title(title):
    return re.sub('[^0-9a-zA-Z]+', '-', title).strip("-").lower()