

#!/bin/bash



rm frog.py
docker exec -it frog rm -rf frog.py
wget -O frog.py https://raw.githubusercontent.com/Lordsniffer22/frogg/main/frog.py
docker cp frog.py frog:/app
rm frog.py
docker restart frog
