FROM flask-image
MAINTAINER drrtuy
EXPOSE 8080 22
RUN apt-get update && apt-get install -y --force-yes ssh vim-tiny
RUN git clone https://github.com/drrtuy/charon /var/www/
#ENTRYPOINT ["/usr/bin/python","/var/www/server.py"]

#passwd
#vim.tiny /etc/ssh/sshd.conf
#service restart ssh
