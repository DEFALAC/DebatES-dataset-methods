'''
This script processes debate data from various sources, including segments, blocks, topics, 
entities, proposals, and fact-checking information. It generates an XML file for each debate
date specified in the `fechas` list. The XML files contain structured information about the debates, 
including participants, interventions, mentions, proposals, claims, and linguistic statistics.
'''

import os
import re
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import xml.etree.ElementTree as ET


debates_metadata ={
    "1993-05-24": {
        "election-date": "1993-06-06",
        "media": "Antena 3"
    },
    "2008-02-25": {
        "election-date": "2008-03-09",
        "media": "AcademiaTV"
    },
    "2008-03-03": {
        "election-date": "2008-03-09",
        "media": "AcademiaTV"
    },
    "2011-11-07": {
        "election-date": "2011-11-20",
        "media": "AcademiaTV"
    },
    "2015-11-23": {
        "election-date": "2015-12-20",
        "media": "Universidad Carlos III"
    },
    "2015-11-30": {
        "election-date": "2015-12-20",
        "media": "El País"
    },
    "2015-12-14": {
        "election-date": "2015-12-20",
        "media": "Atresmedia - AcademiaTV"
    },
    "2016-06-13": {
        "election-date": "2016-06-26",
        "media": "AcademiaTV"
    },
    "2019-04-16": {
        "election-date": "2019-04-28",
        "media": "RTVE"
    },
    "2019-04-20": {
        "election-date": "2019-04-28",
        "media": "La Sexta"
    },
    "2019-04-22": {
        "election-date": "2019-04-28",
        "media": "RTVE"
    },
    "2019-04-23": {
        "election-date": "2019-04-28",
        "media": "Atresmedia"
    },
    "2019-11-01": {
        "election-date": "2019-11-10",
        "media": "RTVE"
    },
    "2019-11-02": {
        "election-date": "2019-11-10",
        "media": "La Sexta"
    },
    "2019-11-04": {
        "election-date": "2019-11-10",
        "media": "AcademiaTV"
    },
    "2019-11-07": {
        "election-date": "2019-11-10",
        "media": "La Sexta"
    },
    "2023-07-10": {
        "election-date": "2023-07-23",
        "media": "Atresmedia"
    },
    "2023-07-13": {
        "election-date": "2023-07-23",
        "media": "RTVE"
    },
    "2023-07-19": {
        "election-date": "2023-07-23",
        "media": "RTVE"
    }
}

def parse_time(time_str):
    try:
        time_obj = datetime.strptime(time_str, "%H:%M:%S.%f")
    except ValueError:
        time_obj = datetime.strptime(time_str, "%M:%S.%f")
    return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second + time_obj.microsecond / 1e6

def load_blocks(filename):
    blocks = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if "<BLOQUE" in line:
                topic = line.split('titulo="')[1].split('"')[0]
                tiempo = parse_time(line.split('tiempo="')[1].split('"')[0])
                blocks.append((topic, tiempo))
    return sorted(blocks, key=lambda x: x[1])

def load_topics(filename):
    topics = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if "<TEMA" in line:
                title = line.split('titulo="')[1].split('"')[0]
                tiempo = parse_time(line.split('tiempo="')[1].split('"')[0])
                topics.append((title, tiempo))
    return sorted(topics, key=lambda x: x[1])

def load_entities(filename):
    elems = []
    with open(filename, "r", encoding="utf-8") as f:
        current_time = None
        current_elems = []
        for line in f:
            if re.match(r"(\d{2}:)?\d{2}:\d{2}\.\d{3}", line):
                if current_time is not None:
                    elems.append((current_time, current_elems))
                current_time = parse_time(re.match(r"(\d{2}:)?\d{2}:\d{2}\.\d{3}", line).group(0))
                current_elems = []
            elif "<MENCION" in line:
                type = line.split('tipo="')[1].split('"')[0]
                texto = line.split('texto="')[1].split('"')[0]
                current_elems.append((type, texto))
        if current_time is not None:
            elems.append((current_time, current_elems))
    return sorted(elems, key=lambda x: x[0])

def load_proposals(filename):
    elems = []
    with open(filename, "r", encoding="utf-8") as f:
        current_time = None
        current_elems = []
        for line in f:
            if re.match(r"(\d{2}:)?\d{2}:\d{2}\.\d{3}", line):
                if current_time is not None:
                    elems.append((current_time, current_elems))
                current_time = parse_time(re.match(r"(\d{2}:)?\d{2}:\d{2}\.\d{3}", line).group(0))
                current_elems = []
            elif "<PROPUESTA" in line:
                resumen = line.split('resumen="')[1].split('"')[0]                
                current_elems.append(resumen)
        if current_time is not None:
            elems.append((current_time, current_elems))
    return sorted(elems, key=lambda x: x[0])

def load_fact_checking(filename):
    elems = []
    with open(filename, "r", encoding="utf-8") as f:
        current_time = None
        current_elems = []
        for line in f:
            if re.match(r"(\d{2}:)?\d{2}:\d{2}\.\d{3}", line):
                if current_time is not None:
                    elems.append((current_time, current_elems))
                current_time = parse_time(re.match(r"(\d{2}:)?\d{2}:\d{2}\.\d{3}", line).group(0))
                current_elems = []
            elif "<REVISABLE" in line:
                statement = line.split('afirmacion="')[1].split('"')[0]                
                current_elems.append(statement)
        if current_time is not None:
            elems.append((current_time, current_elems))
    return sorted(elems, key=lambda x: x[0])

def assign_block(time, blocks):
    for i in range(len(blocks) - 1):
        if blocks[i][1] <= time < blocks[i + 1][1]:
            return blocks[i][0]
    return blocks[-1][0] if blocks else None

def assign_topic(time, topics):
    for i in range(len(topics) - 1):
        if topics[i][1] <= time < topics[i + 1][1]:
            return topics[i][0]
    return topics[-1][0] if topics else None

def assign_entities(time, entities):
    for entity_time, entity_list in entities:
        if entity_time == time:
            return entity_list
    return []

def assign_proposals(time, proposals):
    for fc_time, datos in proposals:
        if fc_time == time:
            return datos
    return None

def assign_fact_checking(time, fact_checking):
    for fc_time, datos in fact_checking:
        if fc_time == time:
            return datos
    return None

def generate_xml(segmentos_csv, blocks_txt, topics_txt, entidades_txt, proposals_txt, fact_checking_txt, speakers_csv, output_xml):
    df = pd.read_csv(segmentos_csv)
    speakers_df = pd.read_csv(speakers_csv)
    blocks = load_blocks(blocks_txt)
    topics = load_topics(topics_txt)
    entities = load_entities(entidades_txt)
    proposals = load_proposals(proposals_txt)
    fact_checking = load_fact_checking(fact_checking_txt)
    

    root = ET.Element("debate", attrib={
        "date": df.iloc[0]["fecha"],
        "election-date": debates_metadata[df.iloc[0]["fecha"]]["election-date"],
        "media": debates_metadata[df.iloc[0]["fecha"]]["media"]
    })
    participants = ET.SubElement(root, "participants")
    participants_dict = {}
    
    for i, row in speakers_df.drop_duplicates(subset=["speaker_name"]).iterrows():
        participant_id = f"p{i}"
        speaker_stats = row
        participants_dict[row["speaker_name"]] = participant_id
        party = df[df["nombre"] == row["speaker_name"]]["partido_nombre"].iloc[0]

        ET.SubElement(
            participants,
            "participant",
            attrib={
            "id": participant_id,
            "full-name": row["speaker_name"],
            "party": party if pd.notna(party) else "",
            "ttr": str(speaker_stats["TTR"]),
            "stop-ratio": str(speaker_stats["STOP_RATIO"]),
            "avg-sent-len": str(speaker_stats["AVG_SENT_LEN"]),
            "avg-dep-per-verb": str(speaker_stats["AVG_DEP_PER_VERB"]),
            "punct-ratio": str(speaker_stats["PUNCT_RATIO"]),
            "adj-ratio": str(speaker_stats["ADJ_RATIO"]),
            "adv-ratio": str(speaker_stats["ADV_RATIO"]),
            "avg-dep-dist": str(speaker_stats["AVG_DEP_DIST"])
            }
        )
    
    blocks_xml = ET.SubElement(root, "blocks")
    blocks_dict = {block_topic: ET.SubElement(blocks_xml, "block", id=f"b{block_id}", topic=block_topic) 
                    for block_id, (block_topic, _) in enumerate(blocks)}
    interventions_dict = {block_topic: ET.SubElement(blocks_dict[block_topic], "interventions") 
                           for block_topic, _ in blocks}
    
    intervention_global_id = 0
    
    for i, row in df.iterrows():
        seg_time = parse_time(row["inicio"])
        block_topic = assign_block(seg_time, blocks)
        topic_asignado = assign_topic(seg_time, topics)
        entidades_asignadas = assign_entities(seg_time, entities) 
        entidades_asignadas = sorted({(type, nombre) for type, nombre in entidades_asignadas}, key=lambda x: (x[0], x[1]))
        proposals_asignadas = assign_proposals(seg_time, proposals)
        fact_checking_asignado = assign_fact_checking(seg_time, fact_checking)

        if block_topic:
            intervention_id = f"i{intervention_global_id:03d}"
            intervention = ET.SubElement(
                interventions_dict[block_topic],
                "intervention",
                attrib={
                    "id": intervention_id,
                    "participant-id": participants_dict[row["nombre"]],
                    "topic": topic_asignado
                }
            )
            intervention_global_id += 1

            if entidades_asignadas:
                entidades_element = ET.SubElement(intervention, "mentions")
                for entidad_id, (type, nombre) in enumerate(entidades_asignadas):
                    ET.SubElement(entidades_element, "mention", id=f"e{entidad_id}", type=type, text=nombre)
            
            if proposals_asignadas:
                proposals_element = ET.SubElement(intervention, "proposals")
                for proposal_id, resumen in enumerate(proposals_asignadas):
                    ET.SubElement(proposals_element, "proposal", id=f"pr{proposal_id}").text = resumen
            
            if fact_checking_asignado:
                claims_element = ET.SubElement(intervention, "claims")
                for claim_id, statement in enumerate(fact_checking_asignado):
                    ET.SubElement(claims_element, "claim", id=f"r{claim_id}").text = statement
            
            stats = ET.SubElement(
                intervention, 
                "linguistic-stats", 
                attrib={
                    "ttr": str(row["TTR"]),
                    "stop-ratio": str(row["STOP_RATIO"]),
                    "avg-sent-len": str(row["AVG_SENT_LEN"]),
                    "avg-dep-per-verb": str(row["AVG_DEP_PER_VERB"]),
                    "punct-ratio": str(row["PUNCT_RATIO"]),
                    "adj-ratio": str(row["ADJ_RATIO"]),
                    "adv-ratio": str(row["ADV_RATIO"]),
                    "avg-dep-dist": str(row["AVG_DEP_DIST"])
                }
            )

            sentences_element = ET.SubElement(intervention, "sentences")
            for sent_id, sentence in enumerate(row["texto"].split(". ")):
                if sentence:
                    ET.SubElement(sentences_element, "sentence", id=f"s{sent_id}").text = sentence.strip()
    
    tree = ET.ElementTree(root)
    ET.indent(tree, space="\t", level=0)
    tree.write(output_xml, encoding="utf-8", xml_declaration=True)
    print(f"Archivo XML generado: {output_xml}")

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

for fecha in fechas:
    print(f"Procesando {fecha}...")
    
    if not all(os.path.exists(f) for f in [
        f"transcriptions/segments/{fecha}/{fecha}_segments.csv",
        f"annotations/blocks/{fecha}.txt",
        f"annotations/topics/{fecha}.txt",
        f"annotations/mentions/{fecha}.txt",
        f"annotations/proposals/{fecha}.txt",
        f"annotations/claims/{fecha}.txt",
        f"transcriptions/segments/{fecha}/{fecha}_speakers.csv"
    ]):
        print(f"Alguno de los ficheros necesarios no existe para la fecha {fecha}.")
        continue

    generate_xml(f"transcriptions/segments/{fecha}/{fecha}_segments.csv",
            f"annotations/blocks/{fecha}.txt",
            f"annotations/topics/{fecha}.txt",
            f"annotations/mentions/{fecha}.txt",
            f"annotations/proposals/{fecha}.txt",
            f"annotations/claims/{fecha}.txt",
            f"transcriptions/segments/{fecha}/{fecha}_speakers.csv",
            f"xml/debate-{fecha}.xml")