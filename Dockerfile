FROM alpine:3

RUN apk update
RUN apk add nodejs npm
RUN apk add python3 python3-dev

RUN ln -s /usr/bin/python3 /usr/bin/python

# if this is called "PIP_VERSION", pip explodes with "ValueError: invalid truth value '<VERSION>'"
ENV PYTHON_PIP_VERSION 20.0.2
# https://github.com/pypa/get-pip
ENV PYTHON_GET_PIP_URL https://github.com/pypa/get-pip/raw/42ad3426cb1ef05863521d7988d5f7fec0c99560/get-pip.py
ENV PYTHON_GET_PIP_SHA256 da288fc002d0bb2b90f6fbabc91048c1fa18d567ad067ee713c6e331d3a32b45

RUN set -ex; \
	\
	wget -O get-pip.py "$PYTHON_GET_PIP_URL"; \
	echo "$PYTHON_GET_PIP_SHA256 *get-pip.py" | sha256sum -c -; \
	\
	python get-pip.py \
		--disable-pip-version-check \
		--no-cache-dir \
		"pip==$PYTHON_PIP_VERSION" \
	; \
	pip --version;

RUN node --version && \
	npm --version && \
	python --version && \
	pip --version

RUN apk add py3-numpy py3-numpy-dev py3-scipy 
RUN apk add py3-twisted
RUN apk add py3-cryptography py3-asn1 py3-bcrypt
RUN apk add py3-xlsxwriter

RUN apk add build-base
RUN pip install --no-cache-dir --disable-pip-version-check pyserial
RUN pip install --no-cache-dir --disable-pip-version-check crc16
RUN pip install --no-cache-dir --disable-pip-version-check pandas

RUN apk add --no-cache libffi-dev openssl-dev
RUN pip install --no-cache-dir --disable-pip-version-check autobahn
RUN pip install --no-cache-dir --disable-pip-version-check wget

RUN apk add --no-cache dos2unix

RUN echo "/src/octopus" >> /usr/lib/python3.8/site-packages/octopus.pth

WORKDIR /src/octopus
COPY package.json .
RUN npm install

COPY twisted/ ./twisted/

COPY rollup.config.js .
COPY octopus/ ./octopus/
RUN ./node_modules/.bin/rollup -c

COPY plugins/ .devcontainer/noop.txt /src/octopus-plugins/
COPY tools/ ./tools/

RUN python tools/install_plugins.py /src/octopus-plugins /usr/lib/python3.8/site-packages
RUN python tools/build.py

WORKDIR /app
COPY start.sh .
RUN dos2unix start.sh
RUN ["chmod", "+x", "start.sh"]

CMD ./start.sh

