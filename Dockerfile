FROM python:3.11-slim-bullseye
WORKDIR /tmp
COPY ./requirements.txt ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
ENV PORT=8080
ENV APP_DIR=/opt
ENV APP_APP=app:app
COPY *.py $APP_DIR
ENTRYPOINT cd $APP_DIR && hypercorn -b 0.0.0.0:$PORT -w 1 --access-logfile '-' $APP_APP
EXPOSE $PORT

