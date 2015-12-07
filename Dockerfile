FROM debian
MAINTAINER drrtuy
EXPOSE 80 443
RUN apt-get update && apt-get install -y --force-yes python python-pip git libpq-dev python-dev vim-tiny
RUN pip install flask
RUN pip install psycopg2
RUN pip install gunicorn
ENTRYPOINT ["bash"]
#ENTRYPOINT ["/usr/bin/python","/var/www/server.py"]
