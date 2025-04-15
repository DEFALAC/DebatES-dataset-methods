'''
This script processes segments from a segments CSV file and generates blocks elements using a generative AI model. 
It reads the segments, formats them, and sends them to the model for processing. 
The results are saved in a text file. The script also handles API rate limiting and logging.
'''

import os
import time
from gemini_api import rate_limited_api_call, configure_api
import csv

def generate_blocks(client, segments_csv, output_txt, log_folder, call_count, start_time):
    """Processes the segments CSV file and generates blocks.
    
    Args:
        client: The generative AI client.
        segments_csv (str): Path to the CSV file with segments.
        output_txt (str): Path to the output text file.
        log_folder (str): Folder to save logs.
        call_count (int): Number of API calls made.
        start_time (float): Start time of the process.
        
    Returns:
        tuple: Updated call count and start time.
    """
    with open(segments_csv, "r", encoding="utf-8") as segments_file:
        reader = csv.DictReader(segments_file)
        segments = [(row['inicio'], row['texto']) for row in reader if row['nombre'] == "MODERADOR"]

    segments_text = "\n============================================================\n\n".join([f'{segment[0]} {segment[1]}' for segment in segments])
        
    response, call_count, start_time = rate_limited_api_call(client, segments_text, call_count, start_time, log_folder)
    with open(output_txt, "w", encoding="utf-8") as output_file:
        cleaned_text = response.text.replace("```xml", "").replace("```", "")
        output_file.write(cleaned_text)
    
    return call_count, start_time


if __name__ == "__main__":
    with open("prompts/system_prompt_blocks.txt", "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()

    MODEL_NAME = "gemini-2.0-flash-exp"
    LOG_FOLDER = "logs"

    SEGMENTS_CSVs = ["transcription/segments/1993-05-24_segments.csv",
        "transcription/segments/2008-02-25/2008-02-25_segments.csv",
        "transcription/segments/2008-03-03/2008-03-03_segments.csv",
        "transcription/segments/2011-11-07/2011-11-07_segments.csv",
        "transcription/segments/2015-11-23/2015-11-23_segments.csv",
        "transcription/segments/2015-11-30/2015-11-30_segments.csv",
        "transcription/segments/2015-12-14/2015-12-14_segments.csv",
        "transcription/segments/2016-06-13/2016-06-13_segments.csv",
        "transcription/segments/2019-04-16/2019-04-16_segments.csv",
        "transcription/segments/2019-04-20/2019-04-20_segments.csv",
        "transcription/segments/2019-04-22/2019-04-22_segments.csv",
        "transcription/segments/2019-04-23/2019-04-23_segments.csv",
        "transcription/segments/2019-11-01/2019-11-01_segments.csv",
        "transcription/segments/2019-11-02/2019-11-02_segments.csv",
        "transcription/segments/2019-11-04/2019-11-04_segments.csv",
        "transcription/segments/2019-11-07/2019-11-07_segments.csv",
        "transcription/segments/2023-07-10/2023-07-10_segments.csv",
        "transcription/segments/2023-07-13/2023-07-13_segments.csv",
        "transcription/segments/2023-07-19/2023-07-19_segments.csv"        
    ]
    OUTPUT_TXTs = [
        "annotations/blocks/1993-05-24.txt",
        "annotations/blocks/2008-02-25.txt",
        "annotations/blocks/2008-03-03.txt",
        "annotations/blocks/2011-11-07.txt",
        "annotations/blocks/2015-11-23.txt",
        "annotations/blocks/2015-11-30.txt",
        "annotations/blocks/2015-12-14.txt",
        "annotations/blocks/2016-06-13.txt",
        "annotations/blocks/2019-04-16.txt",
        "annotations/blocks/2019-04-20.txt",
        "annotations/blocks/2019-04-22.txt",
        "annotations/blocks/2019-04-23.txt",
        "annotations/blocks/2019-11-01.txt",
        "annotations/blocks/2019-11-02.txt",
        "annotations/blocks/2019-11-04.txt",
        "annotations/blocks/2019-11-07.txt",
        "annotations/blocks/2023-07-10.txt",
        "annotations/blocks/2023-07-13.txt",
        "annotations/blocks/2023-07-19.txt"        
    ]


    client = configure_api(MODEL_NAME, SYSTEM_PROMPT)
    call_count, start_time = 0, time.time()
    
    for SEGMENTS_CSV, OUTPUT_TXT in zip(SEGMENTS_CSVs, OUTPUT_TXTs):
        if not os.path.exists(SEGMENTS_CSV):
            print("File not found:", SEGMENTS_CSV)
            exit(1)

        if os.path.exists(OUTPUT_TXT):
            print("Skipping", SEGMENTS_CSV)
            continue

        print("Processing", SEGMENTS_CSV)
        call_count, start_time = generate_blocks(client, SEGMENTS_CSV, OUTPUT_TXT, LOG_FOLDER, call_count, start_time)

