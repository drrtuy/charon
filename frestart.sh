#!/bin/bash

pkill -f python
/entrypoint.sh &
tail -f /var/www/charon/charon.log
