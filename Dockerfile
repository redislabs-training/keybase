FROM docker.io/python:3.9
WORKDIR ./
COPY . /

RUN pip install --no-cache-dir -r requirements.txt
ENV GUNICORN_CMD_ARGS="--workers 1 --bind 0.0.0.0:8000 --log-level debug"
EXPOSE 8000

CMD [ "gunicorn", "wsgi:create_app()" ]