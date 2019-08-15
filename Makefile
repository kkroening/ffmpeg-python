## Automate common development tasks


.PHONY: default
defalt: ffmpeg/detect.json


.tox/py37/bin/python:
	tox -e py37
	touch "$(@)"

.tox/py37/lib/python3.7/site-packages/pandas: .tox/py37/bin/python
	.tox/py37/bin/pip install requests lxml pandas
	touch "$(@)"

.PHONY: ffmpeg/detect.json
ffmpeg/detect.json: .tox/py37/lib/python3.7/site-packages/pandas
	.tox/py37/bin/python examples/get_detect_data.py >"$(@)"

