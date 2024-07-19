

#!/bin/bash


rm keys.py
rm frog.py
docker exec -it frog rm -rf frog.py
wget -O keys.py https://raw.githubusercontent.com/Lordsniffer22/frogg/main/keys.py
wget -O frog.py https://raw.githubusercontent.com/Lordsniffer22/frogg/main/frog.py
docker cp *.py frog:/app
rm frog.py
rm keys.py
docker restart frog
