import os
import logging
from google.cloud import bigquery
from datetime import datetime

def process_file(event, context):
    client = bigquery.Client()
    dataset_name = os.environ.get('DATASET_NAME')

    bucket = event['bucket']
    file_name = event['name']

    try:
        if file_name.lower().endswith('.csv'):
            table_name = os.path.splitext(os.path.basename(file_name))[0]
            table_id = f"{client.project}.{dataset_name}.{table_name}"
            uri = f"gs://{bucket}/{file_name}"
            
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.CSV,
                skip_leading_rows=1,
                time_partitioning=bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field="ingestion_date",  # Existing column to use as ingestion date
                )
            )

            load_job = client.load_table_from_uri(uri, table_id, job_config=job_config)
            load_job.result()

            # Get the table
            table = client.get_table(table_id)

            # Update the 'ingestion_date' column with today's date
            today = datetime.now().strftime('%Y-%m-%d')
            query = f"UPDATE `{table_id}` SET ingestion_date = '{today}' WHERE true"
            query_job = client.query(query)
            query_job.result()

            destination_table = client.get_table(table_id)
            logging.info(f"Loaded {destination_table.num_rows} rows into {table_id}.")
        else:
            logging.warning(f"Ignored file {file_name} as it is not a CSV file.")
    except Exception as e:
        logging.exception(f"Error processing file {file_name}: {str(e)}")
