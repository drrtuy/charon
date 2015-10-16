FROM flask-image
MAINTAINER drrtuy
EXPOSE 8080
COPY app requirements.txt server.py /var/www/
ENTRYPOINT ["/usr/bin/python","/var/www/server.py"]

