### To set up ERPNext with custom applications, you must build a custom Docker image. This method involves defining your apps in a JSON file, encoding it, and passing it as a build argument to the [frappe_docker](https://github.com/frappe/frappe_docker) build process. [1, 2, 3] 

## 1. Create the apps.json file [3] 

Define the applications you want to include. For a standard ERPNext setup with common extensions, your file should look like this:

```
[
  {
    "url": "https://github.com/frappe/erpnext",
    "branch": "version-16"
  },
  {
    "url": "https://github.com/frappe/payments",
    "branch": "version-16"
  },
  {
    "url": "https://github.com/frappe/hrms",
    "branch": "version-16"
  },
  {
    "url": "https://github.com/resilient-tech/india-compliance",
    "branch": "version-16"
  },
  {
    "url": "https://github.com/Mxhran-m/b2r_custom",
    "branch": "main"
  }
]
```


* Note: Ensure the branch matches the version of Frappe you intend to use. [1, 4] 

## 2. Encode apps.json to Base64 [3] 
The build process requires the JSON content as a Base64-encoded string to handle special characters and ensure secure injection. [1, 3] 

```
export APPS_JSON_BASE64=$(base64 -w 0 apps.json)

#To verify the encoding:
echo ${APPS_JSON_BASE64}
```

## 3. Build the Custom Image
Clone the frappe_docker repository and build the image using the encoded string as a build argument. [4, 5] 
```
git clone https://github.com/frappe/frappe_docker
cd frappe_docker
```
```
docker build --build-arg=APPS_JSON_BASE64=$APPS_JSON_BASE64 --tag=my-custom-erpnext:latest --file=images/layered/Containerfile .
```


## 4. Deploy using Docker Compose [6] 
Modify your deployment file (e.g., pwd.yml) to use my-custom-erpnext:latest and update the site creation command to install your apps. [1, 7] 
```
command: >-
  --install-app erpnext
  --install-app hrms
  --install-app payments
```

## 5. Start the Stack
Run the following command to spin up your customized ERPNext instance: [5, 8] 
```
docker compose -p erpnext -f pwd.yml up -d
```
## pwd.yml file

```
services:
  backend:
    image: mxhran/b2r-erp:v0
    pull_policy: never
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
      resources:
        limits:
          memory: 512M
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs

  configurator:
    image: mxhran/b2r-erp:v0
    pull_policy: never
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: none
    entrypoint:
      - bash
      - -c
    command:
      - >
        ls -1 apps > sites/apps.txt;
        bench set-config -g db_host $$DB_HOST;
        bench set-config -gp db_port $$DB_PORT;
        bench set-config -g redis_cache "redis://$$REDIS_CACHE";
        bench set-config -g redis_queue "redis://$$REDIS_QUEUE";
        bench set-config -g redis_socketio "redis://$$REDIS_QUEUE";
        bench set-config -gp socketio_port $$SOCKETIO_PORT;
    environment:
      DB_HOST: db
      DB_PORT: "3306"
      REDIS_CACHE: redis-cache:6379
      REDIS_QUEUE: redis-queue:6379
      SOCKETIO_PORT: "9000"
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs

  create-site:
    image: mxhran/b2r-erp:v0
    pull_policy: never
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: none
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs
    entrypoint:
      - bash
      - -c
    command:
      - >
        wait-for-it -t 120 db:3306;
        wait-for-it -t 120 redis-cache:6379;
        wait-for-it -t 120 redis-queue:6379;
        export start=`date +%s`;
        until [[ -n `grep -hs ^ sites/common_site_config.json | jq -r ".db_host // empty"` ]] && \
          [[ -n `grep -hs ^ sites/common_site_config.json | jq -r ".redis_cache // empty"` ]] && \
          [[ -n `grep -hs ^ sites/common_site_config.json | jq -r ".redis_queue // empty"` ]];
        do
          echo "Waiting for sites/common_site_config.json to be created";
          sleep 5;
          if (( `date +%s`-start > 120 )); then
            echo "could not find sites/common_site_config.json with required keys";
            exit 1
          fi
        done;
        echo "sites/common_site_config.json found";
        if [ -d sites/frontend ]; then
          echo "Site already exists, skipping creation.";
        else
          bench new-site \
            --mariadb-user-host-login-scope='%' \
            --admin-password=admin \
            --db-root-username=root \
            --db-root-password=admin \
            --install-app erpnext \
            --install-app payments \
            --install-app hrms \
            --install-app india_compliance \
            --install-app b2r_custom \
            --set-default frontend;
        fi;

  db:
    image: mariadb:10.6
    networks:
      - frappe_network
    healthcheck:
      test: mysqladmin ping -h localhost --password=admin
      interval: 1s
      retries: 20
    deploy:
      restart_policy:
        condition: on-failure
      resources:
        limits:
          memory: 512M
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --skip-character-set-client-handshake
      - --skip-innodb-read-only-compressed
    environment:
      MYSQL_ROOT_PASSWORD: admin
      MARIADB_ROOT_PASSWORD: admin
    volumes:
      - db-data:/var/lib/mysql

  frontend:
    image: mxhran/b2r-erp:v0
    pull_policy: never
    networks:
      - frappe_network
    depends_on:
      - websocket
    deploy:
      restart_policy:
        condition: on-failure
      resources:
        limits:
          memory: 256M
    command:
      - nginx-entrypoint.sh
    environment:
      BACKEND: backend:8000
      FRAPPE_SITE_NAME_HEADER: frontend
      SOCKETIO: websocket:9000
      UPSTREAM_REAL_IP_ADDRESS: 127.0.0.1
      UPSTREAM_REAL_IP_HEADER: X-Forwarded-For
      UPSTREAM_REAL_IP_RECURSIVE: "off"
      PROXY_READ_TIMEOUT: 120
      CLIENT_MAX_BODY_SIZE: 50m
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs
    ports:
      - "8080:8080"

  queue-long:
    image: mxhran/b2r-erp:v0
    pull_policy: never
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
      resources:
        limits:
          memory: 256M
    command:
      - bench
      - worker
      - --queue
      - long,default,short
    environment:
      FRAPPE_REDIS_CACHE: redis://redis-cache:6379
      FRAPPE_REDIS_QUEUE: redis://redis-queue:6379
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs

  queue-short:
    image: mxhran/b2r-erp:v0
    pull_policy: never
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
      resources:
        limits:
          memory: 256M
    command:
      - bench
      - worker
      - --queue
      - short,default
    environment:
      FRAPPE_REDIS_CACHE: redis://redis-cache:6379
      FRAPPE_REDIS_QUEUE: redis://redis-queue:6379
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs

  redis-queue:
    image: redis:6.2-alpine
    networks:
      - frappe_network
    healthcheck:
      test: redis-cli ping
      interval: 5s
      retries: 10
    deploy:
      restart_policy:
        condition: on-failure
    volumes:
      - redis-queue-data:/data

  redis-cache:
    image: redis:6.2-alpine
    networks:
      - frappe_network
    healthcheck:
      test: redis-cli ping
      interval: 5s
      retries: 10
    deploy:
      restart_policy:
        condition: on-failure
    volumes:
      - redis-cache-data:/data

  scheduler:
    image: mxhran/b2r-erp:v0
    pull_policy: never
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
      resources:
        limits:
          memory: 256M
    command:
      - bench
      - schedule
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs

  websocket:
    image: mxhran/b2r-erp:v0
    pull_policy: never
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
      resources:
        limits:
          memory: 128M
    command:
      - node
      - /home/frappe/frappe-bench/apps/frappe/socketio.js
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs

  backup:
    image: mxhran/b2r-erp:v0
    pull_policy: never
    networks:
      - frappe_network
    deploy:
      restart_policy:
        condition: on-failure
    entrypoint:
      - bash
      - -c
    command:
      - >
        echo "Backup service started. Running every 24 hours.";
        while true; do
          sleep 86400;
          echo "Running backup at $$(date)";
          bench --site frontend backup --with-files;
          echo "Backup completed at $$(date)";
          find /home/frappe/frappe-bench/sites/frontend/private/backups -type f -mtime +7 -delete;
          echo "Old backups cleaned up.";
        done
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs

volumes:
  db-data:
  redis-queue-data:
  redis-cache-data:
  sites:
  logs:

networks:
  frappe_network:
    driver: bridge
```


