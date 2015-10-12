FROM python:3.4

# non-root account for the service
RUN groupadd -r slamon && useradd -r -g slamon slamon 

RUN pip3 install --no-cache-dir psycopg2 gunicorn aiohttp

# Add AFM sources for installation
ADD "setup.py" "/tmp/slamon_afm/"
ADD "slamon_afm" "/tmp/slamon_afm/slamon_afm"

# Install AFM and dependencies with pip
RUN pip install --no-cache-dir /tmp/slamon_afm

# remove extra sources
RUN rm -rf /tmp/slamon_afm

# default to in memory sqlite db
ENV AFM_DB_URI sqlite:////tmp/slamon.db
ENV AFM_WORKERS=4

# Expose the AFM HTTP port
EXPOSE 8080

# Change to a non-root user
USER slamon

CMD ["/bin/sh", "-c", "gunicorn -w ${AFM_WORKERS} -b 0.0.0.0:8080 --env SQLALCHEMY_DATABASE_URI=${AFM_DB_URI} slamon_afm.wsgi:app"]
