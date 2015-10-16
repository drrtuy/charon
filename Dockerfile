FROM flask-image
MAINTAINER drrtuy
EXPOSE 8080
#COPY app requirements.txt server.py /var/www/
RUN git clone https://github.com/drrtuy/charon /var/www/
ENTRYPOINT ["/usr/bin/python","/var/www/charon/server.py"]

