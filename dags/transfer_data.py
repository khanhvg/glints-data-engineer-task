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