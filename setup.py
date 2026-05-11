import os
from setuptools import setup

HICOLOR = os.path.join("share", "icons", "hicolor")
DATA = "data"

data_files = [
    (os.path.join("share", "applications"), [os.path.join(DATA, "io.boxes.Boxes.desktop")]),
]

for size in ("16x16", "32x32", "48x48", "64x64", "128x128", "256x256", "scalable"):
    src = os.path.join(DATA, "icons", "hicolor", size, "apps", "io.boxes.Boxes.svg")
    dst = os.path.join(HICOLOR, size, "apps")
    data_files.append((dst, [src]))

setup(data_files=data_files)
