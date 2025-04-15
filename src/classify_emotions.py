'''
This script processes an XML debate file, sends them to the Gemini API for emotion classification, 
and saves the results in a new XML file.
'''

import time
from gemini_api import configure_api, rate_limited_api_call
import xml.etree.ElementTree as ET

def generate_emotions(xml_path, client, call_count, start_time, log_folder, output_path):
    '''
    Add emotions to sentences in the XML file using the Gemini API.
    Args:
        xml_path (str): Path to the input XML file.
        client: The generative AI client.
        call_count (int): Number of API calls made.
        start_time (float): Start time of the process.
        log_folder (str): Folder to save logs.
        output_path (str): Path to the output XML file.
    '''
    tree = ET.parse(xml_path)
    root = tree.getroot()

    filtered_elements = []
    for intervention in root.findall(".//intervention"):
        new_intervention = ET.Element("intervention", {"id": intervention.attrib.get("id", "")})
        for sentence in intervention.findall(".//sentence"):
            if sentence.text:
                new_sentence = ET.Element("sentence", {"id": sentence.attrib.get("id", "")})
                new_sentence.text = sentence.text.strip()
                new_intervention.append(new_sentence)
        filtered_elements.append(new_intervention)

    filtered_root = ET.Element("debate")
    filtered_root.extend(filtered_elements)
    xml_text = ET.tostring(filtered_root, encoding="unicode")
    response, call_count, start_time = rate_limited_api_call(client, xml_text, call_count, start_time, log_folder)

    model_response_text = response.text
    for line in model_response_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            emotion_elem = ET.fromstring(line)
        except ET.ParseError:
            continue 

        int_id = emotion_elem.attrib.get("int_id")
        sent_id = emotion_elem.attrib.get("sent_id")
        tags = emotion_elem.attrib.get("tags")

        for intervention in filtered_root.findall("intervention"):
            if intervention.attrib.get("id") == int_id:
                for sentence in intervention.findall("sentence"):
                    if sentence.attrib.get("id") == sent_id:
                        sentence.set("emotions", tags)
                        break

    new_xml_text = ET.tostring(filtered_root, encoding="unicode")

    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(new_xml_text)

    return call_count, start_time

if __name__ == "__main__":
    fechas = [
        "1993-05-24",
        "2008-02-25",
        "2008-03-03",
        "2011-11-07",
        "2015-11-23",
        "2015-11-30",
        "2015-12-14",
        "2016-06-13",
        "2019-04-16",
        "2019-04-20",
        "2019-04-22",
        "2019-04-23",
        "2019-11-01",
        "2019-11-02",
        "2019-11-04",
        "2019-11-07",
        "2023-07-10",
        "2023-07-13",
        "2023-07-19"
    ]

    MODEL_NAME = "gemini-2.5-pro-exp-03-25" 
    LOG_FOLDER = "logs"

    with open("prompts/system_prompt_emotions.txt", "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
    
    call_count, start_time = 0, time.time()
    
    for fecha in fechas:
        client = configure_api(MODEL_NAME, SYSTEM_PROMPT)
        print("Procesando fecha", fecha)
        xml_path = f"xml/debate-{fecha}.xml"
        output_path = f"xml/debate-{fecha}-emotions.xml" 
        call_count, start_time = generate_emotions(xml_path, client, call_count, start_time, LOG_FOLDER, output_path)
