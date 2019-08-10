## Automate common development tasks


.PHONY: default
defalt: ffmpeg/detect.json


.tox/py38/bin/python:
	tox -e py38
	touch "$(@)"

.tox/py38/lib/python3.8/site-packages/pandas: .tox/py38/bin/python
	.tox/py38/bin/pip install requests lxml pandas
	touch "$(@)"

.PHONY: ffmpeg/detect.json
ffmpeg/detect.json: .tox/py38/lib/python3.8/site-packages/pandas
	.tox/py38/bin/python examples/get_detect_data.py >"$(@)"

