'''
This script processes VTTC files, segments them into smaller parts, and extracts metadata and linguistic analysis
for each segment. It also generates CSV files with the segmented data and metadata, as well as individual text
files for each segment. The script uses the `compute_ling_stats` module to perform linguistic analysis on the segments.
'''

import csv
import pandas as pd
import os
import json
import compute_ling_stats
from tqdm import tqdm
from collections import defaultdict

def segment_vttc(ruta_fichero, ruta_dir_salida, speakers_ruta_fichero):   
    df = pd.read_csv(speakers_ruta_fichero, encoding='utf-8')
    speakers = {}
    for _, row in df.iterrows():
        speakers[(row['documento'],row['speaker'])] = {'nombre':row['NOMBRE'], 'partido_abreviatura':row['PARTIDO_ABREVIATURA'], 'partido_nombre':row['PARTIDO_NOMBRE']}
    
    documento = ruta_fichero.split("/")[-1].split(".")[0]
    with open(ruta_fichero, 'r', encoding='utf-8') as f:
        lineas = f.readlines()

    segmentos, metadatos, analysis_info, metrics = [], [], [], []
    segments_per_speaker = defaultdict(list)
    analysis_info_per_speaker = defaultdict(list)    
    segmento = ''
    for linea in tqdm(lineas, desc="Procesando líneas",total=len(lineas)):
        if '-->' in linea:
            if segmento:
                # Eliminamos los dobles espacios en blanco
                segmento = segmento.replace('  ', ' ')
                segmentos.append(segmento)                                
                # Si (documento,speaker) no está en el diccionario speakers, lo añadimos con el nombre "MODERADOR", y la abreviatura y nombre de partido ""
                if (documento,speaker) not in speakers:
                    print(f"Speaker no encontrado: {documento}, {speaker}")
                    speakers[(documento,speaker)] = {'nombre':'MODERADOR', 'partido_abreviatura':'', 'partido_nombre':''}

                speaker_name = speakers[(documento,speaker)]['nombre'] 
                metadatos.append({'fecha':documento, 'inicio':inicio, 'fin':fin, 'speaker':speaker, 'nombre':speaker_name, 'partido_abreviatura':speakers[(documento,speaker)]['partido_abreviatura'], 'partido_nombre':speakers[(documento,speaker)]['partido_nombre']})

                segments_per_speaker[speaker_name].append(segmento)

                analysis = compute_ling_stats.analyze_text(segmento)
                analysis_info.append(analysis)
                analysis_info_per_speaker[speaker_name].append(analysis)
                metrics.append(compute_ling_stats.calculate_metrics(analysis))

            segmento = ''
            inicio, fin = linea.split(' --> ')
            inicio = inicio.strip()
            fin = fin.split('[')[0].strip()
            speaker = linea.split('[')[1].split(']')[0]
        else:
            segmento += linea.strip() + ' '

    segmento = segmento.replace('  ', ' ')
    segmentos.append(segmento)                                
    if (documento,speaker) not in speakers:
        speakers[(documento,speaker)] = {'nombre':'MODERADOR', 'partido_abreviatura':'', 'partido_nombre':''}

    speaker_name = speakers[(documento,speaker)]['nombre'] 
    metadatos.append({'fecha':documento, 'inicio':inicio, 'fin':fin, 'speaker':speaker, 'nombre':speaker_name, 'partido_abreviatura':speakers[(documento,speaker)]['partido_abreviatura'], 'partido_nombre':speakers[(documento,speaker)]['partido_nombre']})

    segments_per_speaker[speaker_name].append(segmento)

    analysis = compute_ling_stats.analyze_text(segmento)
    analysis_info.append(analysis)
    analysis_info_per_speaker[speaker_name].append(analysis)
    metrics.append(compute_ling_stats.calculate_metrics(analysis))

    speaker_metrics = []
    for speaker_name, analysis_speaker in tqdm(analysis_info_per_speaker.items(), desc="Calculando métricas por speaker", total=len(analysis_info_per_speaker)):
        metrics_speaker = compute_ling_stats.calculate_metrics_from_list(analysis_speaker)
        metrics_speaker['speaker_name'] = speaker_name
        speaker_metrics.append(metrics_speaker)
    
    df_speaker_metrics = pd.DataFrame(speaker_metrics)
    df_speaker_metrics.to_csv(f'{ruta_dir_salida}/{documento}_speakers.csv', encoding='utf-8', index=False)

    for i, segmento in enumerate(segmentos):     
        segment_subdir = f'{ruta_dir_salida}/segments/{documento}_segment_{i}'
        if not os.path.exists(segment_subdir):
            os.makedirs(segment_subdir)         
        with open(f'{segment_subdir}/{documento}_segment_{i}_text.txt', 'w', encoding='utf-8') as f:
            f.write(segmento)
        

    with open(f'{ruta_dir_salida}/{documento}_sentences.csv', 'w', encoding='utf-8', newline="") as fw_sentences:
        writer_sentences = csv.writer(fw_sentences)
        writer_sentences.writerow(['segment_sentence_index', 'fecha', 'inicio', 'fin', 'speaker', 'nombre', 'partido_abreviatura', 'partido_nombre', 'texto'])
        
        for i, (metadatos_i, analysis_i, metrics_i) in enumerate(zip(metadatos, analysis_info, metrics)):        
            segment_subdir = f'{ruta_dir_salida}/segments/{documento}_segment_{i}'
            if not os.path.exists(segment_subdir):
                os.makedirs(segment_subdir)

            with open(f'{segment_subdir}/{documento}_segment_{i}_metadata.json', 'w', encoding='utf-8') as f:
                f.write(json.dumps(metadatos_i, indent=4))

            with open(f'{segment_subdir}/{documento}_segment_{i}_metrics.json', 'w', encoding='utf-8') as f:
                f.write(json.dumps(metrics_i, indent=4))

            with open(f'{segment_subdir}/{documento}_segment_{i}_tokens.csv', 'w', encoding='utf-8') as fw:
                writer = csv.writer(fw)
                writer.writerow(['sentence_index', 'token_index', 'token_text', 'token_lemma', 'token_pos', 'dep_head_index', 'dep_head_text', 'dep_relation', 'is_stop', 'is_alpha'])
                subdir_sentence = f'{segment_subdir}/dep_trees'
                if not os.path.exists(subdir_sentence):
                        os.makedirs(subdir_sentence)
                for j, s in enumerate(analysis_i['sentences_info']):
                    writer_sentences.writerow([f"{i}_{j}", metadatos_i['fecha'], metadatos_i['inicio'], metadatos_i['fin'], metadatos_i['speaker'], metadatos_i['nombre'], metadatos_i['partido_abreviatura'], metadatos_i['partido_nombre'], s['sentence_text']])
                    
                    with open(f'{subdir_sentence}/{documento}_segment_{i}_sentence_{j}_dep.html', 'w', encoding='utf-8') as f:
                        f.write(analysis_i['dep_htmls'][j])
                    
    df = pd.DataFrame(metadatos)    
    for metric in metrics[0].keys():
        df[metric] = [m[metric] for m in metrics]
    df['texto'] = segmentos
    df.to_csv(f'{ruta_dir_salida}/{documento}_segments.csv', encoding='utf-8', index=False)


if __name__ == "__main__":

    DEBATES = [
        "transcriptions/vttc/1993-05-24.fix.vttc",
        "transcriptions/vttc/2008-02-25.fix.vttc",
        "transcriptions/vttc/2008-03-03.fix.vttc",
        "transcriptions/vttc/2011-11-07.fix.vttc",
        "transcriptions/vttc/2015-11-23.fix.vttc",    
        "transcriptions/vttc/2015-11-30.fix.vttc",
        "transcriptions/vttc/2015-12-14.fix.vttc",
        "transcriptions/vttc/2016-06-13.fix.vttc",
        "transcriptions/vttc/2019-04-16.fix.vttc",
        "transcriptions/vttc/2019-04-20.fix.vttc",
        "transcriptions/vttc/2019-04-22.fix.vttc",
        "transcriptions/vttc/2019-04-23.fix.vttc",
        "transcriptions/vttc/2019-11-01.fix.vttc",
        "transcriptions/vttc/2019-11-02.fix.vttc",
        "transcriptions/vttc/2019-11-04.fix.vttc",
        "transcriptions/vttc/2019-11-07.fix.vttc", 
        "transcriptions/vttc/2023-07-10.fix.vttc",
        "transcriptions/vttc/2023-07-13.fix.vttc",
        "transcriptions/vttc/2023-07-19.fix.vttc"  
    ]

    SALIDAS = [
        "transcriptions/segments/1993-05-24",
        "transcriptions/segments/2008-02-25",
        "transcriptions/segments/2008-03-03",
        "transcriptions/segments/2011-11-07",    
        "transcriptions/segments/2015-11-23",
        "transcriptions/segments/2015-11-30",
        "transcriptions/segments/2015-12-14",
        "transcriptions/segments/2016-06-13",
        "transcriptions/segments/2019-04-16",
        "transcriptions/segments/2019-04-20",
        "transcriptions/segments/2019-04-22",
        "transcriptions/segments/2019-04-23",
        "transcriptions/segments/2019-11-01",
        "transcriptions/segments/2019-11-02",
        "transcriptions/segments/2019-11-04",
        "transcriptions/segments/2019-11-07",
        "transcriptions/segments/2023-07-10",
        "transcriptions/segments/2023-07-13",
        "transcriptions/segments/2023-07-19"  
    ]

    for DEBATE, SALIDA in zip(DEBATES, SALIDAS):
        if not os.path.exists(DEBATE):
            print("File not found:", DEBATE)
            exit(1)
        
        if os.path.exists(SALIDA):
            print("Skipping", DEBATE)
            continue

        print("Procesando debate:", DEBATE)
        if not os.path.exists(SALIDA):
            os.makedirs(SALIDA)

        segment_vttc(DEBATE, SALIDA, "transcriptions/speakers.csv")