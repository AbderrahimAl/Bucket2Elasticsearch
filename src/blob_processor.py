from prefect import flow, task, get_run_logger
from google.cloud import storage
from tika import parser
import os


@task(name="read_blob", log_prints=True)
def read_data(bucket_name: str, file_name: str, logger):
    logger.info(f"bucket_name:  {bucket_name}")
    logger.info(f"file_name: {file_name}")
    try: 
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        with open(file_name, "wb") as file_obj:
            blob.download_to_file(file_obj)
        parsed_content = parser.from_file(file_name)
        text_content = parsed_content['content']
        os.remove(file_name)
        return text_content
    
    except Exception as e:
        logger.error(f"Error processing file: {file_name}: {e}")


@task(name="chunk_text")
def chunk_text(text, min_word_count=300, overlap_prop=0.2):
    chunks = []
    chunk_size = min_word_count
    words = text.replace("\n", " ").replace("\r", " ").replace("\t", " ").strip().split()
    while True:
        overlap_size = int(min_word_count*overlap_prop)
        for start_idx in range(0, len(words), chunk_size):
            start_slice = start_idx - overlap_size
            if start_slice < 0:
                start_slice = 0
            end_slice = start_slice + chunk_size + overlap_size
            if end_slice <= start_slice:
                continue
            text_sample = " ".join(words[start_slice : end_slice])
            chunks.append(text_sample)
        chunk_size = chunk_size * 4
        if chunk_size > len(words):
            break
    return chunks


@flow(name="blob_processor")
def blob_processor(bucket_name: str, file_name: str):
    
    logger = get_run_logger()
    text = read_data(bucket_name, file_name, logger)
    if (".xlsx" not in file_name) or text != '':
        chunks = chunk_text(text)
    else: 
        chunks = []
    logger.info(f"Number of chunks: {len(chunks)}")
    return chunks, file_name


# if __name__ == "__main__":
#     #main_flow(bucket_name="chatbot-bucket-0", file_name="APSPE Onboarding details (1)-1.docx")
    
#     blob_processor.from_source(
#         source="https://github.com/AbderrahimAl/Bucket2Elasticsearch.git", 
#         entrypoint="src/blob_processor.py:blob_processor"
#     ).deploy(
#         name="blob-processor-deployment", 
#         work_pool_name="managed_service_prefect", 
#     )
