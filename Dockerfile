FROM flask-image
MAINTAINER drrtuy
EXPOSE 8080
RUN apt-get update && apt-get install -y --force-yes ssh
RUN git clone https://github.com/drrtuy/charon /var/www/
#ENTRYPOINT ["/usr/bin/python","/var/www/server.py"]

