FROM python:3.11.6

RUN python -m venv myenv
RUN . myenv/bin/activate
COPY . /ems

RUN pip install --upgrade setuptools
RUN pip install -r /ems/requirements.txt
WORKDIR /ems
COPY media/ /media
RUN rm -rf ./media

EXPOSE 8000
RUN chmod +x start.sh
ENTRYPOINT ["sh", "./start.sh"]