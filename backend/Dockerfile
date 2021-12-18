FROM plone/plone-backend:6.0.0a2

LABEL maintainer="Plone Foundation <marketing@plone.org>" \
      org.label-schema.name="ploneorg-backend" \
      org.label-schema.description="Plone.org Backend." \
      org.label-schema.vendor="Plone Foundation" \
      org.label-schema.docker.cmd="docker run -d -p 8080:8080 plone/ploneorg-backend:latest"

# Add local code
COPY . ./
RUN apt-get update \
    && apt-get -y upgrade -y \
    && apt-get -y install make \
    && make VENV=off VENV_FOLDER=. install
