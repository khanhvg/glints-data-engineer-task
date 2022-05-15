# glints-data-engineer-task
## About Assignment
Good Day,

Thank you for applying for the position of Data Engineer at Glints.
The following describe the Technical Assessment requirement for this position.

### Problem Set
A key part of a Data Engineer’s responsibilities is maintaining the serviceability of Data Warehouse. To achieve this, you will need to understand the set up and operation of a basic Data Warehouse.

In this technical assessment, you are required to submit the setup for the data pipeline of a basic data warehouse using Docker and Apache Airflow.

Your final setup should include the following:
- A source postgres database (Database X)
- A target postgres database (Database Y, which is not the same Docker container as Database X)
- Apache Airflow with webserver accessible from localhost:5884
- A Directed Acyclic Graph (DAG) for transferring the content of Source Database X to Target Database Y
- README.md detailing the usage of your submission

As the focus of this technical assessment is on the set up of a basic data pipeline using Airflow, the content of the table in Source Postgres Database X to be transferred can be determined by the candidate. It can be as basic as:

| id | creation_date | sale_value |
| -- | ------------- | ---------- |
| 0  | 12-12-21 | 1000 |
| 1  | 13-12-21 | 2000 |

## Let Solve It
---
To solve this problem, I have used docker compose to create multiple container.

+ apache airflow docker-compose.yml from the document guilde
+ source_postgres container (include to the yml file of apache airflow)
+ target_postgres container (include to the yml file of apache airflow)

A look about docker-compose.yml
```
version: '3.9'

x-airflow-common:
  &airflow-common
  # In order to add custom dependencies or upgrade provider packages you can use your extended image.
  # Comment the image line, place your Dockerfile in the directory where you placed the docker-compose.yaml
  # and uncomment the "build" line below, Then run `docker-compose build` to build the images.
  image: ${AIRFLOW_IMAGE_NAME:-apache/airflow:2.3.0}
  # build: .
  environment:
    &airflow-common-env
    AIRFLOW__CORE__EXECUTOR: CeleryExecutor
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
    # For backward compatibility, with Airflow <2.3
    AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
    AIRFLOW__CELERY__RESULT_BACKEND: db+postgresql://airflow:airflow@postgres/airflow
    AIRFLOW__CELERY__BROKER_URL: redis://:@redis:6379/0
    AIRFLOW__CORE__FERNET_KEY: ''
    AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
    AIRFLOW__CORE__LOAD_EXAMPLES: 'true'
    AIRFLOW__API__AUTH_BACKENDS: 'airflow.api.auth.backend.basic_auth'
    _PIP_ADDITIONAL_REQUIREMENTS: ${_PIP_ADDITIONAL_REQUIREMENTS:-}
  volumes:
    - ./dags:/opt/airflow/dags
    - ./logs:/opt/airflow/logs
    - ./plugins:/opt/airflow/plugins
  user: "${AIRFLOW_UID:-50000}:0"
  depends_on:
    &airflow-common-depends-on
    redis:
      condition: service_healthy
    postgres:
      condition: service_healthy

services:

    # source posgres database
  source-postgres:
    image: postgres:13
    restart: always
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    logging:
      options:
        max-size: 10m
        max-file: "3"
    ports:
      - '5433:5432'
    volumes:
      - ./source-postgres-data:/var/lib/postgresql/data
      - ./sql/create_table.sql:/docker-entrypoint-initdb.d/create_table.sql
      - ./sql/fill_tables.sql:/docker-entrypoint-initdb.d/fill_tables.sql
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 5s
      retries: 5
  
  #target posgres database
  target-postgres:
    image: postgres:13
    restart: always
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    logging:
      options:
        max-size: 10m
        max-file: "3"
    ports:
      - '5434:5432'
    volumes:
      - ./target-postgres-data:/var/lib/postgresql/data
      - ./sql/create_table.sql:/docker-entrypoint-initdb.d/create_table.sql
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 5s
      retries: 5

  postgres:
    image: postgres:13
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - postgres-db-volume:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 5s
      retries: 5
    restart: always

  redis:
    image: redis:latest
    expose:
      - 6379
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 30s
      retries: 50
    restart: always

  airflow-webserver:
    <<: *airflow-common
    command: webserver
    ports:
      - 5884:8080
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:5884/health"]
      interval: 10s
      timeout: 10s
      retries: 5
    restart: always
    depends_on:
      <<: *airflow-common-depends-on
      airflow-init:
        condition: service_completed_successfully

  airflow-scheduler:
    <<: *airflow-common
    command: scheduler
    healthcheck:
      test: ["CMD-SHELL", 'airflow jobs check --job-type SchedulerJob --hostname "$${HOSTNAME}"']
      interval: 10s
      timeout: 10s
      retries: 5
    restart: always
    depends_on:
      <<: *airflow-common-depends-on
      airflow-init:
        condition: service_completed_successfully

  airflow-worker:
    <<: *airflow-common
    command: celery worker
    healthcheck:
      test:
        - "CMD-SHELL"
        - 'celery --app airflow.executors.celery_executor.app inspect ping -d "celery@$${HOSTNAME}"'
      interval: 10s
      timeout: 10s
      retries: 5
    environment:
      <<: *airflow-common-env
      # Required to handle warm shutdown of the celery workers properly
      # See https://airflow.apache.org/docs/docker-stack/entrypoint.html#signal-propagation
      DUMB_INIT_SETSID: "0"
    restart: always
    depends_on:
      <<: *airflow-common-depends-on
      airflow-init:
        condition: service_completed_successfully

  airflow-triggerer:
    <<: *airflow-common
    command: triggerer
    healthcheck:
      test: ["CMD-SHELL", 'airflow jobs check --job-type TriggererJob --hostname "$${HOSTNAME}"']
      interval: 10s
      timeout: 10s
      retries: 5
    restart: always
    depends_on:
      <<: *airflow-common-depends-on
      airflow-init:
        condition: service_completed_successfully

  airflow-init:
    <<: *airflow-common
    entrypoint: /bin/bash
    # yamllint disable rule:line-length
    command:
      - -c
      - |
        function ver() {
          printf "%04d%04d%04d%04d" $${1//./ }
        }
        airflow_version=$$(gosu airflow airflow version)
        airflow_version_comparable=$$(ver $${airflow_version})
        min_airflow_version=2.2.0
        min_airflow_version_comparable=$$(ver $${min_airflow_version})
        if (( airflow_version_comparable < min_airflow_version_comparable )); then
          echo
          echo -e "\033[1;31mERROR!!!: Too old Airflow version $${airflow_version}!\e[0m"
          echo "The minimum Airflow version supported: $${min_airflow_version}. Only use this or higher!"
          echo
          exit 1
        fi
        if [[ -z "${AIRFLOW_UID}" ]]; then
          echo
          echo -e "\033[1;33mWARNING!!!: AIRFLOW_UID not set!\e[0m"
          echo "If you are on Linux, you SHOULD follow the instructions below to set "
          echo "AIRFLOW_UID environment variable, otherwise files will be owned by root."
          echo "For other operating systems you can get rid of the warning with manually created .env file:"
          echo "    See: https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html#setting-the-right-airflow-user"
          echo
        fi
        one_meg=1048576
        mem_available=$$(($$(getconf _PHYS_PAGES) * $$(getconf PAGE_SIZE) / one_meg))
        cpus_available=$$(grep -cE 'cpu[0-9]+' /proc/stat)
        disk_available=$$(df / | tail -1 | awk '{print $$4}')
        warning_resources="false"
        if (( mem_available < 4000 )) ; then
          echo
          echo -e "\033[1;33mWARNING!!!: Not enough memory available for Docker.\e[0m"
          echo "At least 4GB of memory required. You have $$(numfmt --to iec $$((mem_available * one_meg)))"
          echo
          warning_resources="true"
        fi
        if (( cpus_available < 2 )); then
          echo
          echo -e "\033[1;33mWARNING!!!: Not enough CPUS available for Docker.\e[0m"
          echo "At least 2 CPUs recommended. You have $${cpus_available}"
          echo
          warning_resources="true"
        fi
        if (( disk_available < one_meg * 10 )); then
          echo
          echo -e "\033[1;33mWARNING!!!: Not enough Disk space available for Docker.\e[0m"
          echo "At least 10 GBs recommended. You have $$(numfmt --to iec $$((disk_available * 1024 )))"
          echo
          warning_resources="true"
        fi
        if [[ $${warning_resources} == "true" ]]; then
          echo
          echo -e "\033[1;33mWARNING!!!: You have not enough resources to run Airflow (see above)!\e[0m"
          echo "Please follow the instructions to increase amount of resources available:"
          echo "   https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html#before-you-begin"
          echo
        fi
        mkdir -p /sources/logs /sources/dags /sources/plugins
        chown -R "${AIRFLOW_UID}:0" /sources/{logs,dags,plugins}
        exec /entrypoint airflow version
    # yamllint enable rule:line-length
    environment:
      <<: *airflow-common-env
      _AIRFLOW_DB_UPGRADE: 'true'
      _AIRFLOW_WWW_USER_CREATE: 'true'
      _AIRFLOW_WWW_USER_USERNAME: ${_AIRFLOW_WWW_USER_USERNAME:-airflow}
      _AIRFLOW_WWW_USER_PASSWORD: ${_AIRFLOW_WWW_USER_PASSWORD:-airflow}
    user: "0:0"
    volumes:
      - .:/sources

  airflow-cli:
    <<: *airflow-common
    profiles:
      - debug
    environment:
      <<: *airflow-common-env
      CONNECTION_CHECK_MAX_COUNT: "0"
    # Workaround for entrypoint issue. See: https://github.com/apache/airflow/issues/16252
    command:
      - bash
      - -c
      - airflow

  flower:
    <<: *airflow-common
    command: celery flower
    ports:
      - 5555:5555
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:5555/"]
      interval: 10s
      timeout: 10s
      retries: 5
    restart: always
    depends_on:
      <<: *airflow-common-depends-on
      airflow-init:
        condition: service_completed_successfully

volumes:
  postgres-db-volume:
```

To run the following file after git clone my repository:
```
docker-compose up
```
or
```
docker-compose -f docker-compose.yml up
```

Then you can check these container with command:
```
docker ps
```
![docker ps](pic/docker_ps.png)

## Set Up and Configuration
---
### Postgres
---
I have create two container for each postgres and also add the sql command for each postgres when being spinned up that will auto create table and insert data (source_postgres only)
+ For source_postgres I used port 5433
+ For target_postgres I used port 5434
```
# source posgres database
  source-postgres:
    image: postgres:13
    restart: always
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    logging:
      options:
        max-size: 10m
        max-file: "3"
    ports:
      - '5433:5432'
    volumes:
      - ./source-postgres-data:/var/lib/postgresql/data
      - ./sql/create_table.sql:/docker-entrypoint-initdb.d/create_table.sql
      - ./sql/fill_tables.sql:/docker-entrypoint-initdb.d/fill_tables.sql
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 5s
      retries: 5
  
  #target posgres database
  target-postgres:
    image: postgres:13
    restart: always
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    logging:
      options:
        max-size: 10m
        max-file: "3"
    ports:
      - '5434:5432'
    volumes:
      - ./target-postgres-data:/var/lib/postgresql/data
      - ./sql/create_table.sql:/docker-entrypoint-initdb.d/create_table.sql
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 5s
      retries: 5
```

SQL Command that I use to create table
```
-- Create Product Table
CREATE TABLE IF NOT EXISTS product (
  product_id INT NOT NULL UNIQUE,
  product_name VARCHAR(250) NOT NULL,
  price INT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  PRIMARY KEY (product_id)
)
```

SQL Command that I use to insert into table
```
INSERT INTO product VALUES (1,'Lego Batman', 200);
INSERT INTO product VALUES (2,'Lego Spiderman', 300);
INSERT INTO product VALUES (3,'Xbox Controller', 50);
INSERT INTO product VALUES (4,'Nintendo Switch', 320);
INSERT INTO product VALUES (5,'Airpod 3', 170);
INSERT INTO product VALUES (6,'JBL Pulse 4', 200);
```

### Apache Airflow
---
+ I have use the docker-compose.yml that public on [Apache Airflow Document](https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html#docker-compose-yaml)
+ For airflow we use port 5884
+ After running docker-compose up we check the airflow webserver and sign in with username and password is **airflow**
```
http://localhost:5884
```
![airflow home](pic/airflow_home.png)

#### To create connection to two database
First you need to run below command to take the host IP.
```
ipconfig getifaddr en0
```
![Host IP](pic/ipconfig.png)
Then create two database connection
![source_postgres](pic/source_postgres.png)
![target_postgres](pic/target_postgres.png)

---
### Check the Source database
Let use docker ps and take the ID of the source
![docker ps id](pic/docker_ps_id.png)

Then let use docker exec to connect into the container
```
docker exec -it <id> /bin/bash
```
Inside container let connect to the source database use
```
psql -U airflow
```
![inside source container](pic/inside_container.png)

---
Do the same with the target database and we can see the product table have no value
![inside target container](pic/insde_target.png)

### Transfer Data
---
To transfer data from source to target database, we will define dag in transfer_data.py file under dags folder
```
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from airflow.decorators import dag


def transfer_data():
    # Create sql command to select all data from source database
    # Then define a source hook using PostgresHook
    # Then use cursor to execute sql query and fetch all data return
    sql_select = "SELECT product_id,product_name,price FROM product"
    source_hook = PostgresHook(postgres_conn_id="source_postgres")
    source_conn = source_hook.get_conn()
    source_cursor = source_conn.cursor()
    source_cursor.execute(sql_select)
    rows = source_cursor.fetchall()

    # Create target hook with PostgresHook
    # Then using insert_rows function to insert into target database
    target_hook = PostgresHook(postgres_conn_id="target_postgres")
    target_hook.insert_rows(table='product', rows=rows)


@dag(schedule_interval='@once', start_date=datetime(2022, 5, 13), catchup=False)
def transfer_data_postgres():

    PythonOperator(
      task_id = 'transfer_data',
      python_callable = transfer_data
    )

dag = transfer_data_postgres()
```

Let unpause the dag and let it run success
![dag run](pic/dag_run.png)

Let check again the target_postgres
![success](pic/success_transfer.png)
