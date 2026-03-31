# 用法: make install && TOPIC='你的主题' make run
PYTHON ?= python3
PIP ?= pip3

install:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) -m mp_publish run --topic "$(TOPIC)"

dry:
	$(PYTHON) -m mp_publish run --topic "$(TOPIC)" --dry-run-wechat
