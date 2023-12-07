FROM python:3.11.6

RUN python -m venv myenv
RUN . myenv/bin/activate
COPY . /horilla

RUN pip install --upgrade setuptools
RUN pip install -r /horilla/requirements.txt
WORKDIR /horilla
RUN rm TestDB_Horilla.sqlite3
RUN rm -rf ./media
RUN python manage.py makemigrations

COPY start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT [ "/start.sh" ] 