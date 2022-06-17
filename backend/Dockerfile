ARG PLONE_VERSION=6.0.0a4
FROM plone/plone-backend:${PLONE_VERSION}

LABEL maintainer="Plone Foundation <marketing@plone.org>" \
      org.label-schema.name="ploneorg-backend" \
      org.label-schema.description="Plone.org Backend." \
      org.label-schema.vendor="Plone Foundation"

# Add local code
COPY . .

# Install local requirements and fix permissions
RUN ./bin/pip install -r requirements.txt \
    && chown -R plone: /app
