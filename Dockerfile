FROM node:14.15.5-buster-slim AS webpack

WORKDIR /app

RUN apt-get update \
  && apt-get install -y build-essential --no-install-recommends \
  && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
  && apt-get clean \
  && chown node:node -R /app

USER node

COPY --chown=node:node package.json *yarn* rollup.config.js ./

RUN yarn install

ARG NODE_ENV="production"
ENV NODE_ENV="${NODE_ENV}" \
    USER="node"

RUN mkdir -p octopus/blocktopus/resources/blockly/pack/ && mkdir -p octopus/blocktopus/blockly/ && chown node:node -R octopus
COPY --chown=node:node octopus/blocktopus/blockly octopus/blocktopus/blockly

RUN if [ "${NODE_ENV}" != "development" ]; then \
  yarn run build; fi

CMD ["bash"]

#
# App
#

FROM python:3.9.5-slim-buster AS app

WORKDIR /app

RUN apt-get update \
  && apt-get install -y build-essential curl libpq-dev git --no-install-recommends \
  && apt-get install -y libatlas-base-dev libffi-dev libglib2.0-0 libgl1 usbutils dos2unix --no-install-recommends \
  && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
  && apt-get clean \
  && useradd --create-home python \
  && chown python:python -R /app

USER python

# Install requirements and plugins
COPY --chown=python:python requirements*.txt octopus-plugins.txt ./
COPY --chown=python:python bin/ ./bin

RUN chmod 0755 bin/* && dos2unix bin/pip3-install && bin/pip3-install

RUN if [ -f octopus-plugins.txt ]; then pip install -r octopus-plugins.txt; fi

# Set environment variables
ARG OCTOPUS_ENV="production"
ENV OCTOPUS_ENV="${OCTOPUS_ENV}" \
    OCTOPUS_PLUGINS_DIR="/app/plugins" \
    PYTHONUNBUFFERED="true" \
    PYTHONPATH="." \
    PATH="${PATH}:/home/python/.local/bin" \
    USER="python"

# Download the JS/CSS/etc resources if in prodution env
RUN mkdir -p octopus/blocktopus/resources/cache/ && mkdir -p octopus/blocktopus/templates/ && chown python:python -R octopus
RUN mkdir tools && chown python:python tools
COPY --chown=python:python octopus/blocktopus/templates/template-resources.json octopus/blocktopus/templates/template-resources.json
COPY --chown=python:python tools/build.py tools
RUN if [ "$OCTOPUS_ENV" == "production" ]; then \
  python tools/build.py ; fi

# Copy packed javascript from the webpack worker
COPY --chown=python:python --from=webpack /app/octopus/blocktopus/resources/blockly/pack /pack/

# Copy rest of source
COPY --chown=python:python . ./

CMD ["python", "-m", "octopus.blocktopus.server"]


