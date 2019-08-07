## Automate common development tasks


.PHONY: default
defalt: ffmpeg/detect.json


.tox/py35/bin/python:
	tox -e py35
	touch "$(@)"

.tox/py35/lib/python3.5/site-packages/pandas: .tox/py35/bin/python
	.tox/py35/bin/pip install requests lxml pandas
	touch "$(@)"

.PHONY: ffmpeg/detect.json
ffmpeg/detect.json: .tox/py35/lib/python3.5/site-packages/pandas
	.tox/py35/bin/python examples/get_detect_data.py >"$(@)"

