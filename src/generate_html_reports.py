import os
import re
import xml.etree.ElementTree as ET
import json
from collections import defaultdict

def sanitize_filename(name):
    """Return a safe version of the name to use as a filename."""
    return re.sub(r'\W+', '_', name)

def make_link(debate_id, intervention_id, text):
    """
    Build an HTML link pointing to the debate transcript file and the intervention anchor.
    """
    anchor = "intervention_" + intervention_id
    filename = f"debate_{sanitize_filename(debate_id)}_transcription.html"
    return f"<a href='{filename}#{anchor}' target='_blank'>{text}</a>"

def parse_xml_to_transcription_html(xml_path):
    """
    Generates an HTML transcript version of the XML, including anchors.
    """
    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Debate Transcript</title>
  <link href="https://fonts.googleapis.com/css?family=Roboto:400,500,700&display=swap" rel="stylesheet">
  <style>
    /* Global reset and typography */
    * {{ box-sizing: border-box; }}
    body {{ font-family: 'Roboto', sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; color: #333; line-height: 1.6; }}
    a {{ color: #007acc; text-decoration: none; transition: color 0.3s ease; }}
    a:hover {{ color: #005999; text-decoration: underline; }}
    h1, h2, h3 {{ margin: 0 0 15px; font-weight: 500; }}
    header {{ background-color: #007acc; color: #fff; padding: 20px; text-align: center; }}
    .container {{ max-width: 1200px; margin: 20px auto; padding: 0 20px; }}
    .card {{ background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }}
    .block {{ padding: 10px; border-bottom: 1px solid #ccc; margin-bottom: 10px; }}
    .intervention {{ margin-bottom: 15px; padding: 10px; background: #f9f9f9; border-radius: 4px; }}
  </style>
</head>
<body>
  <header><h1>Debate Transcript</h1></header>
  <div class="container">
    <div class="card">
      <h2>Date: {date}</h2>
      <h2>Election date: {election_date}</h2>
      <h2>Media: {media}</h2>
      <h2>Participants</h2>
      <ul>
        {participants}
      </ul>
      {blocks}
    </div>
  </div>
</body>
</html>
"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
        return ""

    date = root.attrib.get("date", "Unknown")
    election_date = root.attrib.get("election-date", "Unknown")
    media = root.attrib.get("media", "Unknown")
    # Process participants
    participants_html = ""
    participants_node = root.find("participants")
    if participants_node is not None:
        for p in participants_node:
            full_name = p.attrib.get("full-name", "Unknown")
            party = p.attrib.get("party", "No party")
            if full_name not in ["MODERADOR", "DECLARACIONES"]:
                participants_html += f"<li><b>{full_name}</b> ({party})</li>"
    # Process blocks and interventions
    blocks_html = ""
    blocks_node = root.find("blocks")
    if blocks_node is not None:
        for block in blocks_node:
            block_id = "block_" + block.attrib.get("id", "")
            topic = block.attrib.get("topic", "")
            blocks_html += f"<div class='block' id='{block_id}'>"
            if topic:
                blocks_html += f"<h2>{topic}</h2>"
            interventions_node = block.find("interventions")
            if interventions_node is not None:
                for intervention in interventions_node:
                    inter_id = "intervention_" + intervention.attrib.get("id", "")
                    participant_id = intervention.attrib.get("participant-id", "")
                    participant = "Unknown"
                    if participants_node is not None:
                        for p in participants_node:
                            if p.attrib.get("id") == participant_id:
                                participant = p.attrib.get("full-name", "Unknown")
                                break
                    blocks_html += f"<div class='intervention' id='{inter_id}'>"
                    blocks_html += f"<h3>{participant}</h3>"
                    inter_topic = intervention.attrib.get("topic", "")
                    if inter_topic:
                        blocks_html += f"<p><b>Topic:</b> {inter_topic}</p>"
                    sentences = intervention.find("sentences")
                    if sentences is not None:
                        blocks_html += "<p><b>Intervention:</b></p>"
                        for sentence in sentences:
                            text = sentence.text or ""
                            blocks_html += f"<p>- {text}</p>"
                    blocks_html += "</div>"
            blocks_html += "</div>"
    return HTML_TEMPLATE.format(date=date, election_date=election_date, media=media, participants=participants_html, blocks=blocks_html)

def parse_participants(participants_node):
    """
    Parses the list of participants and returns a dictionary with ID as the key
    and a dictionary containing 'full-name' and 'party' as the value.
    """
    participants_mapping = {}
    if participants_node is not None:
        for participant in participants_node.findall("participant"):
            pid = participant.get("id")
            full_name = participant.get("full-name", "Unknown").strip()
            party = participant.get("party", "No party").strip()
            participants_mapping[pid] = {"full_name": full_name, "party": party}
    return participants_mapping

def process_intervention(intervention, participants_mapping, global_metrics, speaker_metrics, party_metrics, debate_id):
    intervention_id = intervention.get("id", None)
    pid = intervention.get("participant-id")
    speaker_name = participants_mapping.get(pid, {}).get("full_name", "Unknown")
    speaker_key = speaker_name.strip() if speaker_name.strip() else "Unknown"
    party = participants_mapping.get(pid, {}).get("party", "No party").strip()
    party_key = party if party else "No party"

    # Inicializar métricas del hablante si no existen
    if speaker_key not in speaker_metrics:
        speaker_metrics[speaker_key] = {
            "full_name": speaker_key,
            "party": party,
            "interventions": 0,
            "sentences": 0,
            "words": 0,
            "claims": 0,
            "proposals": 0,
            "fallacies": 0,
            "linguistic_stats": defaultdict(float),
            "linguistic_stats_count": 0,
            "sentence_lengths": [],
            "sentences_per_intervention": [],
            "intervention_word_counts": [],
            "emotions": defaultdict(int),
            "claims_texts": {},
            "proposals_texts": {},
            "fallacies_texts": {},
            "topics": {},
            "debates": set(),
            "emotions_by_debate": {},
            "interventions_emotions": {}
        }

    # Inicializar métricas del partido si no existen
    if party_key not in party_metrics:
        party_metrics[party_key] = {
            "participants": set(),
            "interventions": 0,
            "sentences": 0,
            "words": 0,
            "claims": 0,
            "proposals": 0,
            "fallacies": 0,
            "linguistic_stats": defaultdict(float),
            "linguistic_stats_count": 0,
            "sentence_lengths": [],
            "sentences_per_intervention": [],
            "intervention_word_counts": [],
            "emotions": defaultdict(int),
            "claims_texts": {},
            "proposals_texts": {},
            "fallacies_texts": {},
            "topics": {},
            "debates": set(),
            "emotions_by_debate": {},
            "interventions_emotions": {},
            "intervention_mentions": {}
        }
    party_metrics[party_key]["participants"].add(speaker_key)

    # Actualizar conteos de intervenciones
    speaker_metrics[speaker_key]["interventions"] += 1
    speaker_metrics[speaker_key]["debates"].add(debate_id)
    party_metrics[party_key]["interventions"] += 1
    party_metrics[party_key]["debates"].add(debate_id)

    # Procesar oraciones y contar palabras
    full_intervention_text = ""
    intervention_sentence_count = 0
    intervention_word_count = 0
    sentences_node = intervention.find("sentences")
    if sentences_node is not None:
        sentences_list = sentences_node.findall("sentence")
        full_intervention_text = " ".join(sentence.text.strip() for sentence in sentences_list if sentence.text)
        intervention_sentence_count = len(sentences_list)
        speaker_metrics[speaker_key]["sentences"] += intervention_sentence_count
        party_metrics[party_key]["sentences"] += intervention_sentence_count
        for sentence in sentences_list:
            text = sentence.text or ""
            words = text.split()
            num_words = len(words)
            intervention_word_count += num_words
            speaker_metrics[speaker_key]["words"] += num_words
            party_metrics[party_key]["words"] += num_words
            speaker_metrics[speaker_key]["sentence_lengths"].append(num_words)
            party_metrics[party_key]["sentence_lengths"].append(num_words)
    speaker_metrics[speaker_key]["sentences_per_intervention"].append(intervention_sentence_count)
    speaker_metrics[speaker_key]["intervention_word_counts"].append(intervention_word_count)
    party_metrics[party_key]["sentences_per_intervention"].append(intervention_sentence_count)
    party_metrics[party_key]["intervention_word_counts"].append(intervention_word_count)

    # Procesar estadísticas lingüísticas
    ls_node = intervention.find("linguistic-stats")
    if ls_node is not None:
        for key, value in ls_node.attrib.items():
            try:
                val = float(value)
                speaker_metrics[speaker_key]["linguistic_stats"][key] += val
                speaker_metrics[speaker_key]["linguistic_stats_count"] += 1
                party_metrics[party_key]["linguistic_stats"][key] += val
                party_metrics[party_key]["linguistic_stats_count"] += 1
            except:
                continue

    # Procesar emociones
    emotions_attr = ",".join([sentence.get("emotions", "") for sentence in sentences_node.findall("sentence")])

    intervention_emotions = defaultdict(int)
    if emotions_attr:
        sp_emotions_by_debate = speaker_metrics[speaker_key].setdefault("emotions_by_debate", {})
        sp_emotions_by_debate.setdefault(debate_id, defaultdict(int))
        pt_emotions_by_debate = party_metrics[party_key].setdefault("emotions_by_debate", {})
        pt_emotions_by_debate.setdefault(debate_id, defaultdict(int))
        for emo in [e.strip() for e in emotions_attr.split(",") if e.strip()]:
            speaker_metrics[speaker_key]["emotions"][emo] += 1
            party_metrics[party_key]["emotions"][emo] += 1
            sp_emotions_by_debate[debate_id][emo] += 1
            pt_emotions_by_debate[debate_id][emo] += 1
            intervention_emotions[emo] += 1

    # Almacenar emociones por intervención
    if intervention_id:
        speaker_metrics[speaker_key].setdefault("interventions_emotions", {}).setdefault(debate_id, {})[intervention_id] = dict(intervention_emotions)
        party_metrics[party_key].setdefault("interventions_emotions", {}).setdefault(debate_id, {})[intervention_id] = dict(intervention_emotions)

    # Procesar tema de la intervención
    intervention_topic = intervention.get("topic", "")
    if intervention_id and intervention_topic:
        if intervention_topic not in speaker_metrics[speaker_key]["topics"]:
            speaker_metrics[speaker_key]["topics"][intervention_topic] = {
                "count": 0,
                "debate_id": debate_id,
                "intervention": intervention_id,
                "full_text": ""
            }
        speaker_metrics[speaker_key]["topics"][intervention_topic]["count"] += 1
        speaker_metrics[speaker_key]["topics"][intervention_topic]["full_text"] += " " + full_intervention_text
        if intervention_topic not in party_metrics[party_key]["topics"]:
            party_metrics[party_key]["topics"][intervention_topic] = {
                "count": 0,
                "debate_id": debate_id,
                "intervention": intervention_id,
                "full_text": ""
            }
        party_metrics[party_key]["topics"][intervention_topic]["count"] += 1
        party_metrics[party_key]["topics"][intervention_topic]["full_text"] += " " + full_intervention_text

    # Procesar claims
    claims_node = intervention.find("claims")
    claims_texts = []
    num_claims = 0
    if claims_node is not None:
        claims = claims_node.findall("claim")
        num_claims = len(claims)
        for claim in claims:
            claim_text = claim.text.strip() if claim.text else ""
            if claim_text and intervention_id and speaker_name not in ["MODERADOR", "DECLARACIONES"]:
                formatted_claim = f"{speaker_name}: {claim_text}"
                claims_texts.append((formatted_claim, debate_id, intervention_id, full_intervention_text, speaker_name))
    # Procesar proposals
    proposals_node = intervention.find("proposals")
    proposals_texts = []
    num_proposals = 0
    if proposals_node is not None:
        proposals = proposals_node.findall("proposal")
        num_proposals = len(proposals)
        for proposal in proposals:
            prop_text = proposal.text.strip() if proposal.text else ""
            if prop_text and intervention_id and speaker_name not in ["MODERADOR", "DECLARACIONES"]:
                formatted_proposal = f"{speaker_name}: {prop_text}"
                proposals_texts.append((formatted_proposal, debate_id, intervention_id, full_intervention_text, speaker_name))
    # Procesar fallacies
    fallacies_node = intervention.find("fallacies")
    fallacies_texts = []
    num_fallacies = 0
    if fallacies_node is not None:
        fallacies = fallacies_node.findall("fallacy")
        num_fallacies = len(fallacies)
        for fallacy in fallacies:
            fallacy_text = fallacy.text.strip() if fallacy.text else ""
            formatted_fallacy = f'{speaker_name} ({fallacy.get("category")}): {fallacy_text}'
            fallacies_texts.append((formatted_fallacy, debate_id, intervention_id, full_intervention_text, speaker_name))

    mentions_data = []
    mentions_node = intervention.find("mentions")
    if mentions_node is not None:
        for mention in mentions_node.findall("mention"):
            mentions_data.append({
                "id": mention.get("id", ""),
                "type": mention.get("type", ""),
                "text": mention.get("text", "")
            })
    
    # Almacenar menciones por intervención
    if intervention_id:
        speaker_metrics[speaker_key].setdefault("intervention_mentions", {})[intervention_id] = mentions_data
        party_metrics[party_key].setdefault("intervention_mentions", {})[intervention_id] = mentions_data


    # Actualizar métricas de claims, proposals y fallacies en speaker y party
    speaker_metrics[speaker_key]["claims"] += num_claims
    speaker_metrics[speaker_key]["proposals"] += num_proposals
    speaker_metrics[speaker_key]["fallacies"] += num_fallacies

    party_metrics[party_key]["claims"] += num_claims
    party_metrics[party_key]["proposals"] += num_proposals
    party_metrics[party_key]["fallacies"] += num_fallacies

    # Acumular los textos para claims, proposals y fallacies
    for claim in claims_texts:
        formatted_claim, d_id, i_id, full_text, _ = claim
        speaker_metrics[speaker_key]["claims_texts"][formatted_claim] = (d_id, i_id, full_text)
        party_metrics[party_key]["claims_texts"][formatted_claim] = (d_id, i_id, full_text)
    for proposal in proposals_texts:
        formatted_proposal, d_id, i_id, full_text, _ = proposal
        speaker_metrics[speaker_key]["proposals_texts"][formatted_proposal] = (d_id, i_id, full_text)
        party_metrics[party_key]["proposals_texts"][formatted_proposal] = (d_id, i_id, full_text)
    for fallacy in fallacies_texts:
        formatted_fallacy, d_id, i_id, full_text, _ = fallacy
        speaker_metrics[speaker_key]["fallacies_texts"][formatted_fallacy] = (d_id, i_id, full_text)
        party_metrics[party_key]["fallacies_texts"][formatted_fallacy] = (d_id, i_id, full_text)

    # Devolver los conteos y textos, incluyendo las menciones
    return {
        "intervention_id": intervention_id,
        "speaker_key": speaker_key,
        "party_key": party_key,
        "full_intervention_text": full_intervention_text,
        "intervention_sentence_count": intervention_sentence_count,
        "intervention_word_count": intervention_word_count,
        "intervention_emotions": dict(intervention_emotions),
        "intervention_topic": intervention_topic,
        "num_claims": num_claims,
        "num_proposals": num_proposals,
        "num_fallacies": num_fallacies,
        "claims_texts": claims_texts,
        "proposals_texts": proposals_texts,
        "fallacies_texts": fallacies_texts,
        "mentions": mentions_data  # NUEVA FUNCIONALIDAD: MENCIONES
    }

def process_block(block, participants_mapping, global_metrics, speaker_metrics, party_metrics, debate_id):
    """
    Procesa un bloque, incluyendo sus intervenciones.
    """
    block_topic = block.get("topic", "No Topic")
    interventions_node = block.find("interventions")
    if interventions_node is None:
        return []

    interventions = interventions_node.findall("intervention")
    block_interventions_info = []
    for intervention in interventions:
        intervention_info = process_intervention(intervention, participants_mapping, global_metrics, speaker_metrics, party_metrics, debate_id)
        block_interventions_info.append(intervention_info)
        global_metrics["interventions"] += 1
        global_metrics["sentences"] += intervention_info["intervention_sentence_count"]
        global_metrics["words"] += intervention_info["intervention_word_count"]
        global_metrics["sentence_lengths"].extend([len(sentence.text.split()) for sentence in intervention.find("sentences").findall("sentence") if sentence.text])
        global_metrics["sentences_per_intervention"].append(intervention_info["intervention_sentence_count"])
        global_metrics["intervention_word_counts"].append(intervention_info["intervention_word_count"])
        global_metrics["intervention_topics"][intervention_info["intervention_topic"]] += 1
        global_metrics["claims"] += intervention_info["num_claims"]
        global_metrics["proposals"] += intervention_info["num_proposals"]
        global_metrics["fallacies"] += intervention_info["num_fallacies"]
        for emo, count in intervention_info["intervention_emotions"].items():
            global_metrics["emotions"][emo] += count

    return block_interventions_info

def process_xml(file_path, global_metrics, speaker_metrics, party_metrics):
    """
    Procesa un archivo XML, actualizando las métricas globales, por hablante y por partido.
    También extrae información para vincular propuestas, reclamaciones, falacias y temas.
    Devuelve el debate_id (o None en caso de error).
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

    global_metrics["debates"] += 1
    debate_id = root.get("date", os.path.basename(file_path))
    debate_election_date = root.get("election-date", "")
    debate_media = root.get("media", "")

    # Parsear participantes
    participants_node = root.find("participants")
    participants_mapping = parse_participants(participants_node)

    # Procesar bloques
    blocks = root.findall("blocks/block")
    global_metrics["blocks"] += len(blocks)
    local_blocks_info = []
    local_interventions_info = []
    for block in blocks:
        block_topic = block.get("topic", "No Topic")
        global_metrics["block_topics"][block_topic] += 1
        block_interventions = process_block(block, participants_mapping, global_metrics, speaker_metrics, party_metrics, debate_id)
        local_blocks_info.append({"topic": block_topic, "intervention_count": len(block_interventions)})
        local_interventions_info.extend(block_interventions)

    # Calcular métricas locales del debate
    local_interventions = len(local_interventions_info)
    local_sentences = sum(info["intervention_sentence_count"] for info in local_interventions_info)
    local_words = sum(info["intervention_word_count"] for info in local_interventions_info)
    local_speakers = set(info["speaker_key"] for info in local_interventions_info)
    # Se construye un mapping para los temas, ahora incluyendo "debate_id"
    local_topics_mapping = defaultdict(lambda: {"count": 0, "intervention": None, "full_text": None, "debate_id": debate_id})
    local_claims_mapping = {}
    local_proposals_mapping = {}
    local_fallacies_mapping = {}
    local_interventions_emotions = {info["intervention_id"]: info["intervention_emotions"] for info in local_interventions_info if info["intervention_id"]}
    local_emotions = defaultdict(int)    
    local_num_claims = sum(info["num_claims"] for info in local_interventions_info)
    local_num_proposals = sum(info["num_proposals"] for info in local_interventions_info)
    local_num_fallacies = sum(info["num_fallacies"] for info in local_interventions_info)

    local_intervention_mentions = {}
    for info in local_interventions_info:
        if info["intervention_id"]:
            local_intervention_mentions[info["intervention_id"]] = info.get("mentions", [])

    for info in local_interventions_info:
        topic = info["intervention_topic"]
        local_topics_mapping[topic]["count"] += 1
        if local_topics_mapping[topic]["intervention"] is None:
            local_topics_mapping[topic]["intervention"] = info["intervention_id"]
            local_topics_mapping[topic]["full_text"] = info["full_intervention_text"]
            local_topics_mapping[topic]["debate_id"] = debate_id
            local_topics_mapping[topic]["speaker"] = info["speaker_key"]
        else:
            local_topics_mapping[topic]["full_text"] += " " + info["full_intervention_text"]
            local_topics_mapping[topic]["speaker"] += "," + info["speaker_key"]
        for claim_text, d_id, i_id, full_text, speaker_name in info["claims_texts"]:
            local_claims_mapping[claim_text] = (d_id, i_id, full_text, speaker_name)
        for prop_text, d_id, i_id, full_text, speaker_name in info["proposals_texts"]:
            local_proposals_mapping[prop_text] = (d_id, i_id, full_text, speaker_name)
        for fallacy_text, d_id, i_id, full_text, speaker_name in info["fallacies_texts"]:
            local_fallacies_mapping[fallacy_text] = (d_id, i_id, full_text, speaker_name)

        for emo, count in info["intervention_emotions"].items():
            local_emotions[emo] += count

    # Guardar información del debate, incluyendo las menciones de cada intervención
    global_metrics.setdefault("debates_info", {})[debate_id] = {
        "debate_id": debate_id,
        "date": root.get("date", debate_id),
        "election_date": debate_election_date,
        "media": debate_media,
        "blocks": len(blocks),
        "blocks_info": local_blocks_info,
        "interventions": local_interventions,
        "sentences": local_sentences,
        "words": local_words,
        "speakers": sorted(list(local_speakers)),
        "topics": {k: v for k, v in local_topics_mapping.items()},
        "claims_texts": local_claims_mapping,
        "proposals_texts": local_proposals_mapping,
        "fallacies_texts": local_fallacies_mapping,
        "num_claims": local_num_claims,
        "num_proposals": local_num_proposals,
        "num_fallacies": local_num_fallacies,
        "emotions": dict(local_emotions),
        "intervention_emotions": local_interventions_emotions,
        "intervention_mentions": local_intervention_mentions  # NUEVA FUNCIONALIDAD: MENCIONES
    }
    return debate_id

def generate_emotion_chart_js(emotions, total_interventions, chart_id):
    """
    Generates the JavaScript code for a pie chart of emotions using Chart.js.
    If the canvas is not found, no chart is created.
    """
    sorted_emotions = sorted(emotions.items(), key=lambda x: x[0])
    labels = [emo for emo, _ in sorted_emotions]
    data = [count for _, count in sorted_emotions]
    colors = [
        "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0",
        "#9966FF", "#FF9F40", "#8BC34A", "#CDDC39",
        "#FF5722", "#795548", "#F44336", "#9C27B0"
    ]
    while len(colors) < len(labels):
        colors += colors
    js = f"""
    var canvas = document.getElementById('{chart_id}');
    if (canvas) {{
        var ctx = canvas.getContext('2d');
        window.emotionChart = new Chart(ctx, {{
            type: 'pie',
            data: {{
                labels: {labels},
                datasets: [{{
                    data: {data},
                    backgroundColor: {colors[:len(labels)]},
                    borderColor: '#ffffff',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'bottom',
                        labels: {{
                            font: {{
                                size: 14,
                                family: "'Roboto', sans-serif",
                                weight: '500'
                            }},
                            padding: 20,
                            usePointStyle: true
                        }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                var label = context.label || '';
                                var value = context.parsed;
                                var percentage = ((value / {total_interventions}) * 100).toFixed(1);
                                return label + ': ' + value + ' (' + percentage + '%)';
                            }}
                        }},
                        bodyFont: {{
                            size: 14,
                            family: "'Roboto', sans-serif"
                        }}
                    }}
                }}
            }}
        }});
    }}
    """
    return js

def generate_frames_with_links(frame_title, items):
    """
    Given a list of items, generates an HTML list (<ul>) in which each <li>
    includes the attributes data-debate, data-intervention and data-fulltext (if available).
    """
    html_lines = []
    if items:
        html_lines.append("<ul>")
        for item in items:
            if isinstance(item, dict):
                debate_id = item.get("debate", "")
                intervention_id = item.get("intervention", "")
                link_html = item.get("html", "")
                full_text = item.get("full_text", "")
                speaker = item.get("speaker", "")
                attr = f"data-debate='{debate_id}'"
                if intervention_id:
                    attr += f" data-intervention='{intervention_id}'"
                if speaker:
                    attr += f" data-speaker='{speaker}'"
                if full_text:
                    escaped_full_text = full_text.replace("'", "\\'")
                    attr += f" data-fulltext='{escaped_full_text}'"                
                
                html_lines.append(f"<li {attr}>{link_html}</li>")
            else:
                html_lines.append(f"<li>{item}</li>")
        html_lines.append("</ul>")
    else:
        html_lines.append("<p>No data available.</p>")
    return "\n".join(html_lines)

def generate_debate_html(debate_id, data):
    """Generate the HTML page for a debate with updated layout, filtering and two alternative mentions visualizations."""

    exclude_mention_types = {
        "DATE", "MONEY","PERCENT", "QUANTITY", "TIME"
    }

    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html lang='en'>")
    html.append("<head>")
    html.append("  <meta charset='UTF-8'>")
    html.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html.append(f"  <title>Debate: {debate_id}</title>")
    html.append("  <link href='https://fonts.googleapis.com/css?family=Roboto:400,500,700&display=swap' rel='stylesheet'>")
    html.append("  <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>")
    # Incluir D3.js y d3-cloud
    html.append("  <script src='https://d3js.org/d3.v6.min.js'></script>")
    html.append("  <script src='https://cdnjs.cloudflare.com/ajax/libs/d3-cloud/1.2.5/d3.layout.cloud.min.js'></script>")
    html.append("  <style>")
    html.append(""" 
      * { box-sizing: border-box; }
      body { font-family: 'Roboto', sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; color: #333; line-height: 1.6; }
      a { color: #007acc; text-decoration: none; transition: color 0.3s ease; }
      a:hover { color: #005999; text-decoration: underline; }
      h1, h2, h3 { margin: 0 0 15px; font-weight: 500; }
      header { background-color: #007acc; color: #fff; padding: 20px; text-align: center; }
      .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
      .card { background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }
      .frames-container { display: block; }
      .frame { margin-bottom: 20px; }
      .scroll-box { max-height: 400px; overflow-y: auto; padding: 10px; border: 1px solid #ccc; margin-top: 10px; }
      table { width: 100%; border-collapse: collapse; }
      th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
      th { background-color: #007acc; color: #fff; }
      tr:nth-child(even) { background-color: #f9f9f9; }
      .emotions-container { display: flex; flex-wrap: wrap; gap: 20px; }
      .emotions-container .table-wrapper, .emotions-container .chart-wrapper { flex: 1 1 45%; max-width: 45%; }
      .chart-container { position: relative; margin: 20px auto; height: 350px; width: 350px; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 20px; }
      #debateFilters { position: fixed; top: 120px; right: 20px; z-index: 1000; width: 250px; }
      /* Aumentar el tamaño vertical de la visualización de menciones */
      #mentionsCloud, #mentionsAltContainer { min-height: 400px; }
      /* Estilos para la Alternative View */
      #mentionsAltContainer { overflow: hidden; }
      #mentionsBarChart { float: left; width: 50%; }
      #mentionsTableContainer { float: right; width: 45%; overflow-y: auto; }
      /* Estilos para el toggle switch */
      .switch {
        position: relative;
        display: inline-block;
        width: 50px;
        height: 24px;
        vertical-align: middle;
      }
      .switch input {display:none;}
      .slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: #ccc;
        transition: .4s;
        border-radius: 24px;
      }
      .slider:before {
        position: absolute;
        content: "";
        height: 18px;
        width: 18px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: .4s;
        border-radius: 50%;
      }
      input:checked + .slider {
        background-color: #007acc;
      }
      input:checked + .slider:before {
        transform: translateX(26px);
      }
      /* Estilos para el switch de visualización */
      #mentionsSwitch { margin-bottom: 10px; }
      #mentionsSwitchLabel { font-size: 14px; margin-left: 8px; vertical-align: middle; }
    """)
    html.append("  </style>")
    html.append("</head>")
    html.append("<body>")
    html.append(f"  <header><h1>Debate: {debate_id}</h1></header>")
    html.append("  <div class='container'>")
    html.append("    <div class='card'>")
    transcription_filename = f"debate_{sanitize_filename(debate_id)}_transcription.html"
    html.append(f"      <p><a href='{transcription_filename}' target='_blank'><strong>View Full Debate Transcription</strong></a></p>")
    html.append(f"      <p><strong>Date:</strong> {data['date']} &nbsp;&nbsp;&nbsp; <strong>Election date:</strong> {data['election_date']} &nbsp;&nbsp;&nbsp; <strong>Media:</strong> {data['media']}</p>")
    html.append("      <h2>Metrics</h2>")
    html.append("      <ul>")
    html.append(f"        <li><strong>Blocks:</strong> {data['blocks']}</li>")
    html.append(f"        <li><strong>Interventions:</strong> {data['interventions']}</li>")
    html.append(f"        <li><strong>Sentences:</strong> {data['sentences']}</li>")
    html.append(f"        <li><strong>Words:</strong> {data['words']}</li>")
    html.append("      </ul>")
    html.append("      <h3>Participants</h3>")
    if "speakers" in data and data["speakers"]:
        html.append("      <ul>")
        for speaker in data["speakers"]:
            if speaker not in ["MODERADOR", "DECLARACIONES"]:
                html.append(f"        <li>{speaker}</li>")
        html.append("      </ul>")
    else:
        html.append("      <p>No participants recorded.</p>")
    html.append("      <h3>Blocks</h3>")
    if "blocks_info" in data and data["blocks_info"]:
        html.append("      <ul>")
        for block in data["blocks_info"]:
            html.append(f"        <li><strong>{block['topic']}</strong> - {block['intervention_count']} interventions</li>")
        html.append("      </ul>")
    else:
        html.append("      <p>No blocks recorded.</p>")
    html.append("      <div id='debateFilters' class='card'>")
    html.append("        <h3>Filter</h3>")
    html.append("        <div id='speakerCheckboxes'>")
    html.append("          <ul>")
    for speaker in data["speakers"]:
        if speaker not in ["MODERADOR", "DECLARACIONES"]:
            html.append(f"            <li><label><input type='checkbox' class='speakerCheckbox' value='{speaker}' checked> {speaker}</label></li>")
    html.append("          </ul>")
    html.append("        </div>")
    html.append("        <input type='text' id='keywordFilter' placeholder='Enter keyword'><br>")
    html.append("        <div><label><input type='checkbox' id='matchWholeWord'> Match whole word</label></div>")
    html.append("      </div>")
    html.append("      <div class='frames-container'>")
    topics_links = [ {"debate": debate_id, 
                      "intervention": info["intervention"],
                      "html": make_link(debate_id, info["intervention"],  f"[{info['debate_id']}] {topic} ({info['count']} {'intervention' if info['count']==1 else 'interventions'})"),
                      "full_text": info.get("full_text", ""),
                      "speaker": info.get("speaker", "")}
                     for topic, info in data["topics"].items() if topic]
    html.append("        <div class='frame intervention-topics'><h3>Intervention Topics</h3><div class='scroll-box'>" +
                generate_frames_with_links("Intervention Topics", topics_links) + "</div></div>")
    proposals_links = []
    for text, values in data["proposals_texts"].items():
        if len(values) >= 3:
            debate_id_val, inter_id, full_text, speaker = values
        else:
            debate_id_val, inter_id = values
            full_text = ""
        proposals_links.append({
            "debate": debate_id_val,
            "intervention": inter_id,
            "html": make_link(debate_id_val, inter_id, f"[{debate_id_val}] " + text),
            "full_text": full_text,
            "speaker": speaker
        })
    html.append("        <div class='frame'><h3>Proposals</h3><div class='scroll-box'>" +
                generate_frames_with_links("Proposals", proposals_links) + "</div></div>")
    claims_links = []
    for text, values in data["claims_texts"].items():
        if len(values) >= 3:
            debate_id_val, inter_id, full_text, speaker = values
        else:
            debate_id_val, inter_id = values
            full_text = ""
        claims_links.append({
            "debate": debate_id_val,
            "intervention": inter_id,
            "html": make_link(debate_id_val, inter_id, f"[{debate_id_val}] " + text),
            "full_text": full_text,
            "speaker": speaker
        })
    html.append("        <div class='frame'><h3>Claims</h3><div class='scroll-box'>" +
                generate_frames_with_links("Claims", claims_links) + "</div></div>")
    fallacies_links = []
    for text, values in data.get("fallacies_texts", {}).items():
        if len(values) >= 3:
            debate_id_val, inter_id, full_text, speaker = values
        else:
            debate_id_val, inter_id = values
            full_text = ""
        fallacies_links.append({
            "debate": debate_id_val,
            "intervention": inter_id,
            "html": make_link(debate_id_val, inter_id, f"[{debate_id_val}] " + text),
            "full_text": full_text,
            "speaker": speaker
        })
    html.append("        <div class='frame'><h3>Fallacies</h3><div class='scroll-box'>" +
                generate_frames_with_links("Fallacies", fallacies_links) + "</div></div>")
    html.append("      </div>")
    html.append("      <h3>Emotions</h3>")
    html.append("      <div class='emotions-container'>")
    html.append("         <div class='table-wrapper'>")
    html.append("             <table id='emotionTable'>")
    html.append("                <tr><th>Emotion</th><th>Sentences</th><th>Percentage</th></tr>")
    for emo, count in sorted(data["emotions"].items(), key=lambda x: x[0]):
        pct = (count / data["interventions"] * 100) if data["interventions"] else 0
        html.append(f"                <tr><td>{emo}</td><td>{count}</td><td>{pct:.1f}%</td></tr>")
    html.append("             </table>")
    html.append("         </div>")
    html.append("         <div class='chart-wrapper'>")
    html.append("             <div class='chart-container'><canvas id='emotionChart'></canvas></div>")
    html.append("         </div>")
    html.append("      </div>")
    html.append("      <div id='interventionEmotions' style='display:none;'>" + json.dumps(data["intervention_emotions"]) + "</div>")
    # Eliminamos de data["intevention_mentions"] los tipos de menciones indicados en exclude_mention_types
    filtered_mentions = {id_intervention: [
        mention for mention in list_mentions if mention["type"] not in exclude_mention_types
    ] for id_intervention, list_mentions in data["intervention_mentions"].items()}
    html.append("      <div id='interventionMentions' style='display:none;'>" + json.dumps(filtered_mentions) + "</div>")
    # Sección de Mentions con toggle switch de visualización
    html.append("      <h3>Mentions</h3>")
    html.append("      <div id='mentionsSwitch'>")
    html.append("        <label class='switch'>")
    html.append("          <input type='checkbox' id='mentionsToggle' checked>")
    html.append("          <span class='slider'></span>")
    html.append("        </label>")
    html.append("        <span id='mentionsSwitchLabel'>Frequency per type</span>")
    html.append("      </div>")
    # Contenedor para la Alternative View (Frequency per type)
    html.append("      <div id='mentionsAltContainer' style='display:block;'>")
    html.append("          <div id='mentionsBarChart'></div>")
    html.append("          <div id='mentionsTableContainer'></div>")
    html.append("          <div style='clear:both;'></div>")
    html.append("      </div>")
    # Contenedor para la Word Cloud (oculto por defecto)
    html.append("      <div id='mentionsCloudContainer' style='display:none;'>")
    html.append("          <div id='mentionsCloud'></div>")
    html.append("          <div id='mentionsLegend' style='margin-top:10px;'></div>")
    html.append("      </div>")
    html.append("      <p><a href='index.html'>← Back to index</a></p>")
    html.append("    </div>")
    # Declarar activeMentionTypes y demás funciones en el script
    html.append("    <script>")
    html.append(generate_emotion_chart_js(data["emotions"], data["interventions"], "emotionChart"))
    html.append("""
    // Declarar activeMentionTypes globalmente para la Word Cloud
    var activeMentionTypes = {};

    document.addEventListener("DOMContentLoaded", function() {        
        const keywordInput = document.getElementById("keywordFilter");
        const matchWholeWordChk = document.getElementById("matchWholeWord");
        const speakerCheckboxes = document.querySelectorAll("#speakerCheckboxes input[type=checkbox]");
                
        function filtrarElementos() {
            let speakersSeleccionados = Array.from(speakerCheckboxes)
                .filter(chk => chk.checked)
                .map(chk => chk.value);
            const keyword = keywordInput.value.trim().toLowerCase();
            const useWholeWord = matchWholeWordChk.checked; 
            const elementos = document.querySelectorAll(".frames-container li[data-debate]");
            elementos.forEach(item => {
                const speakers = item.getAttribute("data-speaker");
                const isInterventionTopic = item.closest('.intervention-topics') !== null;
                const textToSearch = isInterventionTopic 
                    ? (item.getAttribute("data-fulltext") || "").toLowerCase() 
                    : item.textContent.toLowerCase();
                let matchesSpeaker = speakers && speakersSeleccionados.some(s => speakers.includes(s));
                let matchesKeyword = true;
                if (keyword) {
                    if (useWholeWord) {
                        const words = textToSearch.match(/[\p{L}\d]+/gu);
                        matchesKeyword = words.includes(keyword);
                    } else {
                        matchesKeyword = textToSearch.includes(keyword);
                    }
                }
                item.style.display = (matchesSpeaker && matchesKeyword) ? "" : "none";
            });
            updateEmotions();
            updateMentionsView();
        }
        speakerCheckboxes.forEach(chk => chk.addEventListener("change", filtrarElementos));
        keywordInput.addEventListener("input", filtrarElementos);
        matchWholeWordChk.addEventListener("change", filtrarElementos);        
        filtrarElementos();
    
        function updateEmotions() {
            var visibleInterventions = new Set();
            var selectedSpeakers = new Set();
            document.querySelectorAll("#speakerCheckboxes input[type=checkbox]:checked").forEach(function(checkbox) {
                selectedSpeakers.add(checkbox.value);
            });
            document.querySelectorAll(".frames-container li[data-intervention]:not([style*='display: none'])").forEach(function(item) {
                var speaker = item.getAttribute("data-speaker");
                if (selectedSpeakers.has(speaker)) {
                    visibleInterventions.add(item.getAttribute("data-intervention"));
                }
            });
            var interventionEmotionsData = JSON.parse(document.getElementById('interventionEmotions').innerText || '{}');
            var newEmotions = {};
            for (var interId in interventionEmotionsData) {
                if (visibleInterventions.has(interId)) {
                    for (var emo in interventionEmotionsData[interId]) {
                        newEmotions[emo] = (newEmotions[emo] || 0) + interventionEmotionsData[interId][emo];
                    }
                }
            }
            var totalCount = 0;
            for (var emo in newEmotions) {
                totalCount += newEmotions[emo];
            }
            var sortedEmos = Object.keys(newEmotions).sort();
            var tableHTML = "<tr><th>Emotion</th><th>Sentences</th><th>Percentage</th></tr>";
            sortedEmos.forEach(function(emo) {
                var count = newEmotions[emo] || 0;
                var pct = totalCount > 0 ? ((count / totalCount) * 100).toFixed(1) : "0.0";
                tableHTML += "<tr><td>" + emo + "</td><td>" + count + "</td><td>" + pct + "%</td></tr>";
            });
            document.getElementById("emotionTable").innerHTML = tableHTML;
            var labels = sortedEmos;
            var dataArr = labels.map(function(emo){ return newEmotions[emo] || 0; });
            if (window.emotionChart) {
                window.emotionChart.data.labels = labels;
                window.emotionChart.data.datasets[0].data = dataArr;
                window.emotionChart.update();
            }
        }
        
        // Función para actualizar la vista de menciones según el estado del toggle switch
        function updateMentionsView() {
            var toggle = document.getElementById("mentionsToggle");
            var switchLabel = document.getElementById("mentionsSwitchLabel");
            if (toggle.checked) {
                // Frequency per type view
                switchLabel.innerText = "Frequency per type";
                document.getElementById("mentionsAltContainer").style.display = "block";
                document.getElementById("mentionsCloudContainer").style.display = "none";
                updateAltMentions();
            } else {
                // Word cloud view
                switchLabel.innerText = "Word cloud";
                document.getElementById("mentionsAltContainer").style.display = "none";
                document.getElementById("mentionsCloudContainer").style.display = "block";
                updateCloudMentions();
            }
        }
        
        // Actualización de la Word Cloud (vista antigua)
        function updateCloudMentions() {
            var visibleInterventions = new Set();
            document.querySelectorAll(".frames-container li[data-intervention]:not([style*='display: none'])").forEach(function(item) {
                visibleInterventions.add(item.getAttribute("data-intervention"));
            });
            var interventionMentionsData = JSON.parse(document.getElementById('interventionMentions').innerText || '{}');
            var mentionsFrequency = {};
            for (var interId in interventionMentionsData) {
                if (visibleInterventions.has(interId)) {
                    var mentionsArray = interventionMentionsData[interId];
                    mentionsArray.forEach(function(mention) {
                        var key = mention.text + "|" + mention.type;
                        if (!mentionsFrequency[key]) {
                            mentionsFrequency[key] = { count: 0, text: mention.text, type: mention.type };
                        }
                        mentionsFrequency[key].count += 1;
                    });
                }
            }
            var maxCount = 0;
            var wordsData = [];
            for (var key in mentionsFrequency) {
                if (mentionsFrequency[key].count > maxCount) {
                    maxCount = mentionsFrequency[key].count;
                }
                mentionsFrequency[key].text = mentionsFrequency[key].text; //+ " (" + mentionsFrequency[key].count + ")";
                wordsData.push(mentionsFrequency[key]);
            }
            wordsData.forEach(function(d) {
                if (!(d.type in activeMentionTypes)) {
                    activeMentionTypes[d.type] = true;
                }
            });
            var filteredWordsData = wordsData.filter(function(d) {
                return activeMentionTypes[d.type];
            });
            var fontSizeScale = d3.scaleLinear()
                                  .domain([0, maxCount])
                                  .range([12, 42]);
            var wordsForCloud = filteredWordsData.map(function(d) {
                return { text: d.text, size: fontSizeScale(d.count), type: d.type, count: d.count };
            });
            var container = d3.select("#mentionsCloud");
            container.selectAll("*").remove();
            var width = container.node().getBoundingClientRect().width;
            var height = 600;
            var uniqueTypes = Array.from(new Set(wordsData.map(function(d) { return d.type; })));
            var colorScale = d3.scaleOrdinal().domain(uniqueTypes).range(d3.schemeSet2);
            function drawCloud(words) {
                var svg = container.append("svg")
                                   .attr("width", width)
                                   .attr("height", height)
                                   .append("g")
                                   .attr("transform", "translate(" + width/2 + "," + height/2 + ")");
                var cloud = svg.selectAll("text")
                               .data(words, function(d) { return d.text; });
                cloud.enter()
                     .append("text")
                     .style("font-family", "Impact")
                     .style("fill", function(d) { return colorScale(d.type); })
                     .attr("text-anchor", "middle")
                     .attr("font-size", 1)
                     .text(function(d) { return d.text; })
                     .transition()
                     .duration(600)
                     .style("font-size", function(d) { return d.size + "px"; })
                     .attr("transform", function(d) { return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")"; })
                     .style("fill-opacity", 1);
                cloud.exit()
                     .transition()
                     .duration(200)
                     .style("fill-opacity", 1e-6)
                     .attr("font-size", 1)
                     .remove();
            }
            d3.layout.cloud().size([width, height])
                .words(wordsForCloud)
                .padding(5)
                .rotate(function() { return ~~(Math.random() * 2) * 90; })
                .font("Impact")
                .fontSize(function(d) { return d.size; })
                .on("end", drawCloud)
                .start();
                
            var legendHTML = "<p style='font-size:12px; color:#555; margin:0 0 5px 0;'>Click on each type to filter</p><strong>Legend:</strong> ";
            uniqueTypes.forEach(function(type) {
                var isActive = activeMentionTypes[type];
                var squareStyle = "width:12px; height:12px; display:inline-block; margin-right:5px; cursor:pointer;";
                if (isActive) {
                    squareStyle += "background:" + colorScale(type) + ";";
                } else {
                    squareStyle += "border: 2px solid " + colorScale(type) + ";";
                }
                legendHTML += "<span class='legend-item' data-type='" + type + "' style='cursor:pointer; margin-right:10px;'>";
                legendHTML += "<span style='" + squareStyle + "'></span>" + type + "</span>";
            });
            document.getElementById("mentionsLegend").innerHTML = legendHTML;
            document.querySelectorAll(".legend-item").forEach(function(item) {
                item.addEventListener("click", function() {
                    var type = this.getAttribute("data-type");
                    activeMentionTypes[type] = !activeMentionTypes[type];
                    updateCloudMentions();
                });
            });
        }
        
        // Actualización de la Alternative View: Bar Chart + Table (Frequency per type)
        function updateAltMentions() {
            // Limpiar contenedores
            d3.select("#mentionsBarChart").selectAll("*").remove();
            document.getElementById("mentionsTableContainer").innerHTML = "";
            var visibleInterventions = new Set();
            document.querySelectorAll(".frames-container li[data-intervention]:not([style*='display: none'])").forEach(function(item) {
                visibleInterventions.add(item.getAttribute("data-intervention"));
            });
            var interventionMentionsData = JSON.parse(document.getElementById('interventionMentions').innerText || '{}');
            // Calcular frecuencias por tipo
            var typeFrequency = {};
            for (var interId in interventionMentionsData) {
                if (visibleInterventions.has(interId)) {
                    var mentionsArray = interventionMentionsData[interId];
                    mentionsArray.forEach(function(mention) {
                        typeFrequency[mention.type] = (typeFrequency[mention.type] || 0) + 1;
                    });
                }
            }
            var dataTypes = [];
            for (var t in typeFrequency) {
                dataTypes.push({ type: t, count: typeFrequency[t] });
            }
            dataTypes.sort(function(a, b) { return b.count - a.count; });
            var chartMargin = {top: 20, right: 20, bottom: 20, left: 120};  // Aumentamos el margen izquierdo
            var chartWidth = document.getElementById("mentionsBarChart").clientWidth - chartMargin.left - chartMargin.right;
            var chartHeight = 600 //dataTypes.length * 30;
            // Asignar altura al contenedor de la tabla para que coincida con la gráfica
            document.getElementById("mentionsTableContainer").style.height = chartHeight + "px";
            var svg = d3.select("#mentionsBarChart")
                        .append("svg")
                        .attr("width", chartWidth + chartMargin.left + chartMargin.right)
                        .attr("height", chartHeight + chartMargin.top + chartMargin.bottom)
                        .append("g")
                        .attr("transform", "translate(" + chartMargin.left + "," + chartMargin.top + ")");
            // Añadir texto indicativo sobre la gráfica (fuera del SVG)
            d3.select("#mentionsBarChart").insert("p",":first-child")
              .attr("style", "font-size:12px; color:#555; margin:0 0 5px 0;")
              .text("Click on a type to see its frequencies");
            var yScale = d3.scaleBand()
                           .domain(dataTypes.map(function(d){ return d.type; }))
                           .range([0, chartHeight])
                           .padding(0.1);
            var xScale = d3.scaleLinear()
                           .domain([0, d3.max(dataTypes, function(d){ return d.count; })])
                           .range([0, chartWidth]);
            var uniqueTypes = dataTypes.map(function(d){ return d.type; });
            var colorScale = d3.scaleOrdinal().domain(uniqueTypes).range(d3.schemeSet2);
            // Dibujar barras
            svg.selectAll(".bar")
               .data(dataTypes)
               .enter()
               .append("rect")
               .attr("class", "bar")
               .attr("y", function(d){ return yScale(d.type); })
               .attr("height", yScale.bandwidth())
               .attr("x", 0)
               .attr("width", function(d){ return xScale(d.count); })
               .attr("fill", function(d){ return colorScale(d.type); })
               .style("cursor", "pointer")
               .on("click", function(event, d) {
                    updateMentionsTable(d.type);
               });
            // Dibujar etiquetas del eje vertical con tamaño de fuente menor (11px) y mayor desplazamiento
            svg.selectAll(".label")
               .data(dataTypes)
               .enter()
               .append("text")
               .attr("class", "label")
               .attr("x", -10)
               .attr("y", function(d){ return yScale(d.type) + yScale.bandwidth()/2; })
               .attr("dy", ".35em")
               .attr("text-anchor", "end")
               .style("font-size", "11px")
               .text(function(d){ return d.type; })
               .style("cursor", "pointer")
               .on("click", function(event, d) {
                    updateMentionsTable(d.type);
               });
            // Inicializar la tabla con el primer tipo (si existe)
            if (dataTypes.length > 0) {
                 updateMentionsTable(dataTypes[0].type);
            }
        }
        
        // Función para actualizar la tabla de la Alternative View con encabezado fijo (thead sticky)
        function updateMentionsTable(selectedType) {
            var visibleInterventions = new Set();
            document.querySelectorAll(".frames-container li[data-intervention]:not([style*='display: none'])").forEach(function(item) {
                visibleInterventions.add(item.getAttribute("data-intervention"));
            });
            var interventionMentionsData = JSON.parse(document.getElementById('interventionMentions').innerText || '{}');
            var mentionFreq = {};
            for (var interId in interventionMentionsData) {
                if (visibleInterventions.has(interId)) {
                    var mentionsArray = interventionMentionsData[interId];
                    mentionsArray.forEach(function(mention) {
                        if (mention.type === selectedType) {
                            mentionFreq[mention.text] = (mentionFreq[mention.text] || 0) + 1;
                        }
                    });
                }
            }
            var mentionData = [];
            for (var text in mentionFreq) {
                 mentionData.push({ text: text, count: mentionFreq[text] });
            }
            mentionData.sort(function(a, b) { return b.count - a.count; });
            // Crear encabezado fijo y contenedor para la tabla con scroll.          
            var headerHtml = "<div style='font-size:12px; color:#333; margin:0; padding:4px; border-bottom:1px solid #ddd;'>Mentions for type: " + selectedType + "</div>";
            var tableHtml = "<div style='overflow-y:auto; max-height:550px;'><table style='width:100%; border-collapse: collapse; font-size:12px;'>" +
                            "<thead style='position:sticky; top:0; background:#fff;'><tr><th style='border:1px solid #ddd; padding:4px;'>Mention</th><th style='border:1px solid #ddd; padding:4px;'>Frequency</th></tr></thead>" +
                            "<tbody>";
            mentionData.forEach(function(d) {
                 tableHtml += "<tr><td style='border:1px solid #ddd; padding:4px;'>" + d.text + "</td><td style='border:1px solid #ddd; padding:4px; text-align:right;'>" + d.count + "</td></tr>";
            });
            tableHtml += "</tbody></table>";
            document.getElementById("mentionsTableContainer").innerHTML = headerHtml + tableHtml;
        }
        
        // Agregar listener al toggle switch
        document.getElementById("mentionsToggle").addEventListener("change", updateMentionsView);
        
        // Inicializar la vista de menciones (por defecto Frequency per type)
        updateMentionsView();
    });
    """)
    html.append("    </script>")
    html.append("  </div>")
    html.append("</body>")
    html.append("</html>")
    return "\n".join(html)


def generate_party_html(party, data):
    """Generate the HTML page for a party."""
    proposals_links = []
    for text, values in data["proposals_texts"].items():
        if len(values) >= 3:
            debate_id_val, inter_id, full_text = values
        else:
            debate_id_val, inter_id = values
            full_text = ""
        proposals_links.append({
            "debate": debate_id_val,
            "intervention": inter_id,
            "html": make_link(debate_id_val, inter_id, f"[{debate_id_val}] " + text),
            "full_text": full_text
        })
    claims_links = []
    for text, values in data["claims_texts"].items():
        if len(values) >= 3:
            debate_id_val, inter_id, full_text = values
        else:
            debate_id_val, inter_id = values
            full_text = ""
        claims_links.append({
            "debate": debate_id_val,
            "intervention": inter_id,
            "html": make_link(debate_id_val, inter_id, f"[{debate_id_val}] " + text),
            "full_text": full_text
        })
    topics_links = [ {"debate": info["debate_id"], 
                      "intervention": info["intervention"],
                      "html": make_link(info["debate_id"], info["intervention"], f"[{info['debate_id']}] {topic} ({info['count']} {'intervention' if info['count']==1 else 'interventions'})"),
                      "full_text": info.get("full_text", "")}
                    for topic, info in data["topics"].items() ]
    fallacies_links = []
    for text, values in data.get("fallacies_texts", {}).items():
        if len(values) >= 3:
            debate_id_val, inter_id, full_text = values
        else:
            debate_id_val, inter_id = values
            full_text = ""
        fallacies_links.append({
            "debate": debate_id_val,
            "intervention": inter_id,
            "html": make_link(debate_id_val, inter_id, f"[{debate_id_val}] " + text),
            "full_text": full_text
        })

    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html lang='en'>")
    html.append("<head>")
    html.append("  <meta charset='UTF-8'>")
    html.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html.append(f"  <title>Party: {party}</title>")
    html.append("  <link href='https://fonts.googleapis.com/css?family=Roboto:400,500,700&display=swap' rel='stylesheet'>")
    html.append("  <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>")
    # Incluir D3.js y d3-cloud para visualización de menciones
    html.append("  <script src='https://d3js.org/d3.v6.min.js'></script>")
    html.append("  <script src='https://cdnjs.cloudflare.com/ajax/libs/d3-cloud/1.2.5/d3.layout.cloud.min.js'></script>")
    html.append("  <style>")
    html.append(""" 
      * { box-sizing: border-box; }
      body { font-family: 'Roboto', sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; color: #333; line-height: 1.6; }
      a { color: #007acc; text-decoration: none; transition: color 0.3s ease; }
      a:hover { color: #005999; text-decoration: underline; }
      h1, h2, h3 { margin: 0 0 15px; font-weight: 500; }
      header { background-color: #007acc; color: #fff; padding: 20px; text-align: center; }
      .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
      .card { background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }
      #debateFilters { position: fixed; top: 120px; right: 20px; z-index: 1000; width: 250px; }
      .frames-container { display: block; }
      .frame { margin-bottom: 20px; }
      .scroll-box { max-height: 400px; overflow-y: auto; padding: 10px; border: 1px solid #ccc; margin-top: 10px; }
      table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
      th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
      th { background-color: #007acc; color: #fff; }
      tr:nth-child(even) { background-color: #f9f9f9; }
      .emotions-container { display: flex; flex-wrap: wrap; gap: 20px; }
      .emotions-container .table-wrapper, .emotions-container .chart-wrapper { flex: 1 1 45%; max-width: 45%; }
      .chart-container { position: relative; margin: 20px auto; height: 350px; width: 350px; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 20px; }
      /* Estilos para visualización de menciones */
      #mentionsCloud, #mentionsAltContainer { min-height: 400px; }
      #mentionsAltContainer { overflow: hidden; }
      #mentionsBarChart { float: left; width: 50%; }
      #mentionsTableContainer { float: right; width: 45%; overflow-y: auto; }
      .switch {
        position: relative;
        display: inline-block;
        width: 50px;
        height: 24px;
        vertical-align: middle;
      }
      .switch input {display:none;}
      .slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: #ccc;
        transition: .4s;
        border-radius: 24px;
      }
      .slider:before {
        position: absolute;
        content: "";
        height: 18px;
        width: 18px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: .4s;
        border-radius: 50%;
      }
      input:checked + .slider {
        background-color: #007acc;
      }
      input:checked + .slider:before {
        transform: translateX(26px);
      }
      #mentionsSwitch { margin-bottom: 10px; }
      #mentionsSwitchLabel { font-size: 14px; margin-left: 8px; vertical-align: middle; }
    """)
    html.append("  </style>")
    html.append("</head>")
    html.append("<body>")
    html.append(f"  <header><h1>Party: {party}</h1></header>")
    html.append("  <div class='container'>")
    html.append("    <div class='card'>")
    html.append("      <h2>Metrics</h2>")
    html.append("      <ul>")
    html.append(f"        <li><strong>Debates:</strong> {len(data['debates'])}</li>")
    html.append(f"        <li><strong>Participants:</strong> {len(data['participants'])}</li>")
    html.append(f"        <li><strong>Interventions:</strong> {data['interventions']}</li>")
    html.append(f"        <li><strong>Sentences:</strong> {data['sentences']}</li>")
    html.append(f"        <li><strong>Words:</strong> {data['words']}</li>")
    html.append("      </ul>")
    html.append("      <div id='debateFilters' class='card'>")
    html.append("        <h3>Filter by Debates</h3>")
    html.append("        <div id='debateCheckboxes'>")
    html.append("          <ul>")
    for debate in sorted(data["debates"]):
        html.append(f"            <li><label><input type='checkbox' class='debateCheckbox' value='{debate}' checked> {debate}</label></li>")
    html.append("          </ul>")
    html.append("        </div>")
    html.append("        <input type='text' id='keywordFilter' placeholder='Filter by keyword'><br>")
    html.append("        <div><label><input type='checkbox' id='matchWholeWord'> Match whole word</label></div>")
    html.append("      </div>")
    html.append("      <div id='interventionEmotions' style='display:none;'>" + json.dumps(data["interventions_emotions"]) + "</div>")
    html.append("      <div class='frames-container'>")
    html.append("        <div class='frame intervention-topics'><h3>Intervention Topics</h3><div class='scroll-box'>" + generate_frames_with_links("Intervention Topics", topics_links) + "</div></div>")
    html.append("        <div class='frame'><h3>Proposals</h3><div class='scroll-box'>" + generate_frames_with_links("Proposals", proposals_links) + "</div></div>")
    html.append("        <div class='frame'><h3>Claims</h3><div class='scroll-box'>" + generate_frames_with_links("Claims", claims_links) + "</div></div>")
    html.append("        <div class='frame'><h3>Fallacies</h3><div class='scroll-box'>" + generate_frames_with_links("Fallacies", fallacies_links) + "</div></div>")
    html.append("      </div>")
    html.append("      <h3>Emotions</h3>")
    html.append("      <div class='emotions-container'>")
    html.append("         <div class='table-wrapper'>")
    html.append("             <table id='emotionTable'>")
    html.append("                <tr><th>Emotion</th><th>Sentences</th><th>Percentage</th></tr>")
    for emo, count in sorted(data["emotions"].items(), key=lambda x: x[0]):
        pct = (count / data["interventions"] * 100) if data["interventions"] else 0
        html.append(f"                <tr><td>{emo}</td><td>{count}</td><td>{pct:.1f}%</td></tr>")
    html.append("             </table>")
    html.append("         </div>")
    html.append("         <div class='chart-wrapper'>")
    html.append("             <div class='chart-container'><canvas id='emotionChart'></canvas></div>")
    html.append("         </div>")
    html.append("      </div>")
    # Sección de Mentions
    exclude_mention_types = {"DATE", "MONEY", "PERCENT", "QUANTITY", "TIME"}
    filtered_mentions = {id_intervention: [
        mention for mention in list_mentions if mention["type"] not in exclude_mention_types
    ] for id_intervention, list_mentions in data["intervention_mentions"].items()}
    html.append("      <div id='interventionMentions' style='display:none;'>" + json.dumps(filtered_mentions) + "</div>")
    html.append("      <h3>Mentions</h3>")
    html.append("      <div id='mentionsSwitch'>")
    html.append("        <label class='switch'>")
    html.append("          <input type='checkbox' id='mentionsToggle' checked>")
    html.append("          <span class='slider'></span>")
    html.append("        </label>")
    html.append("        <span id='mentionsSwitchLabel'>Frequency per type</span>")
    html.append("      </div>")
    html.append("      <div id='mentionsAltContainer' style='display:block;'>")
    html.append("          <div id='mentionsBarChart'></div>")
    html.append("          <div id='mentionsTableContainer'></div>")
    html.append("          <div style='clear:both;'></div>")
    html.append("      </div>")
    html.append("      <div id='mentionsCloudContainer' style='display:none;'>")
    html.append("          <div id='mentionsCloud'></div>")
    html.append("          <div id='mentionsLegend' style='margin-top:10px;'></div>")
    html.append("      </div>")
    html.append("      <p><a href='index.html'>← Back to index</a></p>")
    html.append("    </div>")
    html.append("    <script>")
    html.append(generate_emotion_chart_js(data["emotions"], data["interventions"], "emotionChart"))
    html.append("""
    document.addEventListener("DOMContentLoaded", function() {
        const debateCheckboxes = document.querySelectorAll("#debateCheckboxes input[type=checkbox]");
        const keywordInput = document.getElementById("keywordFilter");
        const matchWholeWordChk = document.getElementById("matchWholeWord");        
        
        function filtrarElementos() {
            let debatesSeleccionados = Array.from(debateCheckboxes)
                .filter(chk => chk.checked)
                .map(chk => chk.value);
            const keyword = keywordInput ? keywordInput.value.trim().toLowerCase() : "";
            const useWholeWord = matchWholeWordChk ? matchWholeWordChk.checked : false;
            const elementos = document.querySelectorAll(".frames-container li[data-debate][data-intervention]");
            elementos.forEach(item => {
                const debate = item.getAttribute("data-debate");
                const isInterventionTopic = item.closest('.intervention-topics') !== null;
                const textToSearch = isInterventionTopic 
                    ? (item.getAttribute("data-fulltext") || "").toLowerCase()
                    : item.textContent.toLowerCase();
                let matchesDebate = debatesSeleccionados.includes(debate);
                let matchesKeyword = true;
                if (keyword) {
                    if (useWholeWord) {
                        const words = textToSearch.match(/[\p{L}\d]+/gu);
                        matchesKeyword = words.includes(keyword);
                    } else {
                        matchesKeyword = textToSearch.includes(keyword);
                    }
                }
                item.style.display = (matchesDebate && matchesKeyword) ? "" : "none";
            });
            updateEmotions();
            updateMentionsView();
        }
        debateCheckboxes.forEach(chk => chk.addEventListener("change", filtrarElementos));
        keywordInput.addEventListener("input", filtrarElementos);
        matchWholeWordChk.addEventListener("change", filtrarElementos);        
        filtrarElementos();
    
        function updateEmotions() {
            var selectedDebates = Array.from(debateCheckboxes)
                .filter(chk => chk.checked)
                .map(chk => chk.value);
            var visibleInterventionsByDebate = {};
            document.querySelectorAll(".frames-container li[data-debate][data-intervention]:not([style*='display: none'])").forEach(function(item) {
                var debate = item.getAttribute("data-debate");
                var interId = item.getAttribute("data-intervention");
                if (selectedDebates.includes(debate)) {
                    if (!visibleInterventionsByDebate[debate]) {
                        visibleInterventionsByDebate[debate] = new Set();
                    }
                    visibleInterventionsByDebate[debate].add(interId);
                }
            });
            var interventionEmotionsData = JSON.parse(document.getElementById('interventionEmotions').innerText || '{}');
            var newEmotions = {};
            for (var debate in interventionEmotionsData) {
                if (selectedDebates.includes(debate) && visibleInterventionsByDebate[debate]) {
                    for (var interId in interventionEmotionsData[debate]) {
                        if (visibleInterventionsByDebate[debate].has(interId)) {
                            for (var emo in interventionEmotionsData[debate][interId]) {
                                newEmotions[emo] = (newEmotions[emo] || 0) + interventionEmotionsData[debate][interId][emo];
                            }
                        }
                    }
                }
            }
            var totalCount = 0;
            for (var emo in newEmotions) {
                totalCount += newEmotions[emo];
            }
            var sortedEmos = Object.keys(newEmotions).sort();
            var tableHTML = "<tr><th>Emotion</th><th>Sentences</th><th>Percentage</th></tr>";
            sortedEmos.forEach(function(emo) {
                var count = newEmotions[emo] || 0;
                var pct = totalCount > 0 ? ((count / totalCount) * 100).toFixed(1) : "0.0";
                tableHTML += "<tr><td>" + emo + "</td><td>" + count + "</td><td>" + pct + "%</td></tr>";
            });
            document.getElementById("emotionTable").innerHTML = tableHTML;
            var labels = sortedEmos;
            var dataArr = labels.map(function(emo){ return newEmotions[emo] || 0; });
            if (window.emotionChart) {
                window.emotionChart.data.labels = labels;
                window.emotionChart.data.datasets[0].data = dataArr;
                window.emotionChart.update();
            }
        }
        
        // Declarar activeMentionTypes globalmente para la Word Cloud
        var activeMentionTypes = {};

        // Función para actualizar la vista de menciones según el estado del toggle switch
        function updateMentionsView() {
            var toggle = document.getElementById("mentionsToggle");
            var switchLabel = document.getElementById("mentionsSwitchLabel");
            if (toggle.checked) {
                // Frequency per type view
                switchLabel.innerText = "Frequency per type";
                document.getElementById("mentionsAltContainer").style.display = "block";
                document.getElementById("mentionsCloudContainer").style.display = "none";
                updateAltMentions();
            } else {
                // Word cloud view
                switchLabel.innerText = "Word cloud";
                document.getElementById("mentionsAltContainer").style.display = "none";
                document.getElementById("mentionsCloudContainer").style.display = "block";
                updateCloudMentions();
            }
        }
        
        // Actualización de la Word Cloud (vista antigua)
        function updateCloudMentions() {
            var visibleInterventions = new Set();
            document.querySelectorAll(".frames-container li[data-intervention]:not([style*='display: none'])").forEach(function(item) {
                visibleInterventions.add(item.getAttribute("data-intervention"));
            });
            var interventionMentionsData = JSON.parse(document.getElementById('interventionMentions').innerText || '{}');
            var mentionsFrequency = {};
            for (var interId in interventionMentionsData) {
                if (visibleInterventions.has(interId)) {
                    var mentionsArray = interventionMentionsData[interId];
                    mentionsArray.forEach(function(mention) {
                        var key = mention.text + "|" + mention.type;
                        if (!mentionsFrequency[key]) {
                            mentionsFrequency[key] = { count: 0, text: mention.text, type: mention.type };
                        }
                        mentionsFrequency[key].count += 1;
                    });
                }
            }
            var maxCount = 0;
            var wordsData = [];
            for (var key in mentionsFrequency) {
                if (mentionsFrequency[key].count > maxCount) {
                    maxCount = mentionsFrequency[key].count;
                }
                wordsData.push(mentionsFrequency[key]);
            }
            wordsData.forEach(function(d) {
                if (!(d.type in activeMentionTypes)) {
                    activeMentionTypes[d.type] = true;
                }
            });
            var filteredWordsData = wordsData.filter(function(d) {
                return activeMentionTypes[d.type];
            });
            var fontSizeScale = d3.scaleLinear()
                                  .domain([0, maxCount])
                                  .range([12, 42]);
            var wordsForCloud = filteredWordsData.map(function(d) {
                return { text: d.text, size: fontSizeScale(d.count), type: d.type, count: d.count };
            });
            var container = d3.select("#mentionsCloud");
            container.selectAll("*").remove();
            var width = container.node().getBoundingClientRect().width;
            var height = 600;
            var uniqueTypes = Array.from(new Set(wordsData.map(function(d) { return d.type; })));
            var colorScale = d3.scaleOrdinal().domain(uniqueTypes).range(d3.schemeSet2);
            function drawCloud(words) {
                var svg = container.append("svg")
                                   .attr("width", width)
                                   .attr("height", height)
                                   .append("g")
                                   .attr("transform", "translate(" + width/2 + "," + height/2 + ")");
                var cloud = svg.selectAll("text")
                               .data(words, function(d) { return d.text; });
                cloud.enter()
                     .append("text")
                     .style("font-family", "Impact")
                     .style("fill", function(d) { return colorScale(d.type); })
                     .attr("text-anchor", "middle")
                     .attr("font-size", 1)
                     .text(function(d) { return d.text; })
                     .transition()
                     .duration(600)
                     .style("font-size", function(d) { return d.size + "px"; })
                     .attr("transform", function(d) { return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")"; })
                     .style("fill-opacity", 1);
                cloud.exit()
                     .transition()
                     .duration(200)
                     .style("fill-opacity", 1e-6)
                     .attr("font-size", 1)
                     .remove();
            }
            d3.layout.cloud().size([width, height])
                .words(wordsForCloud)
                .padding(5)
                .rotate(function() { return ~~(Math.random() * 2) * 90; })
                .font("Impact")
                .fontSize(function(d) { return d.size; })
                .on("end", drawCloud)
                .start();
                
            var legendHTML = "<p style='font-size:12px; color:#555; margin:0 0 5px 0;'>Click on each type to filter</p><strong>Legend:</strong> ";
            uniqueTypes.forEach(function(type) {
                var isActive = activeMentionTypes[type];
                var squareStyle = "width:12px; height:12px; display:inline-block; margin-right:5px; cursor:pointer;";
                if (isActive) {
                    squareStyle += "background:" + colorScale(type) + ";";
                } else {
                    squareStyle += "border: 2px solid " + colorScale(type) + ";";
                }
                legendHTML += "<span class='legend-item' data-type='" + type + "' style='cursor:pointer; margin-right:10px;'>";
                legendHTML += "<span style='" + squareStyle + "'></span>" + type + "</span>";
            });
            document.getElementById("mentionsLegend").innerHTML = legendHTML;
            document.querySelectorAll(".legend-item").forEach(function(item) {
                item.addEventListener("click", function() {
                    var type = this.getAttribute("data-type");
                    activeMentionTypes[type] = !activeMentionTypes[type];
                    updateCloudMentions();
                });
            });
        }
        
        // Actualización de la Alternative View: Bar Chart + Table (Frequency per type)
        function updateAltMentions() {
            d3.select("#mentionsBarChart").selectAll("*").remove();
            document.getElementById("mentionsTableContainer").innerHTML = "";
            var visibleInterventions = new Set();
            document.querySelectorAll(".frames-container li[data-intervention]:not([style*='display: none'])").forEach(function(item) {
                visibleInterventions.add(item.getAttribute("data-intervention"));
            });
            var interventionMentionsData = JSON.parse(document.getElementById('interventionMentions').innerText || '{}');
            var typeFrequency = {};
            for (var interId in interventionMentionsData) {
                if (visibleInterventions.has(interId)) {
                    var mentionsArray = interventionMentionsData[interId];
                    mentionsArray.forEach(function(mention) {
                        typeFrequency[mention.type] = (typeFrequency[mention.type] || 0) + 1;
                    });
                }
            }
            var dataTypes = [];
            for (var t in typeFrequency) {
                dataTypes.push({ type: t, count: typeFrequency[t] });
            }
            dataTypes.sort(function(a, b) { return b.count - a.count; });
            var chartMargin = {top: 20, right: 20, bottom: 20, left: 120};
            var chartWidth = document.getElementById("mentionsBarChart").clientWidth - chartMargin.left - chartMargin.right;
            var chartHeight = 600;
            document.getElementById("mentionsTableContainer").style.height = chartHeight + "px";
            var svg = d3.select("#mentionsBarChart")
                        .append("svg")
                        .attr("width", chartWidth + chartMargin.left + chartMargin.right)
                        .attr("height", chartHeight + chartMargin.top + chartMargin.bottom)
                        .append("g")
                        .attr("transform", "translate(" + chartMargin.left + "," + chartMargin.top + ")");
            d3.select("#mentionsBarChart").insert("p",":first-child")
              .attr("style", "font-size:12px; color:#555; margin:0 0 5px 0;")
              .text("Click on a type to see its frequencies");
            var yScale = d3.scaleBand()
                           .domain(dataTypes.map(function(d){ return d.type; }))
                           .range([0, chartHeight])
                           .padding(0.1);
            var xScale = d3.scaleLinear()
                           .domain([0, d3.max(dataTypes, function(d){ return d.count; })])
                           .range([0, chartWidth]);
            var uniqueTypes = dataTypes.map(function(d){ return d.type; });
            var colorScale = d3.scaleOrdinal().domain(uniqueTypes).range(d3.schemeSet2);
            svg.selectAll(".bar")
               .data(dataTypes)
               .enter()
               .append("rect")
               .attr("class", "bar")
               .attr("y", function(d){ return yScale(d.type); })
               .attr("height", yScale.bandwidth())
               .attr("x", 0)
               .attr("width", function(d){ return xScale(d.count); })
               .attr("fill", function(d){ return colorScale(d.type); })
               .style("cursor", "pointer")
               .on("click", function(event, d) {
                    updateMentionsTable(d.type);
               });
            svg.selectAll(".label")
               .data(dataTypes)
               .enter()
               .append("text")
               .attr("class", "label")
               .attr("x", -10)
               .attr("y", function(d){ return yScale(d.type) + yScale.bandwidth()/2; })
               .attr("dy", ".35em")
               .attr("text-anchor", "end")
               .style("font-size", "11px")
               .text(function(d){ return d.type; })
               .style("cursor", "pointer")
               .on("click", function(event, d) {
                    updateMentionsTable(d.type);
               });
            if (dataTypes.length > 0) {
                 updateMentionsTable(dataTypes[0].type);
            }
        }
        
        // Función para actualizar la tabla de la Alternative View con encabezado fijo (thead sticky)
        function updateMentionsTable(selectedType) {
            var visibleInterventions = new Set();
            document.querySelectorAll(".frames-container li[data-intervention]:not([style*='display: none'])").forEach(function(item) {
                visibleInterventions.add(item.getAttribute("data-intervention"));
            });
            var interventionMentionsData = JSON.parse(document.getElementById('interventionMentions').innerText || '{}');
            var mentionFreq = {};
            for (var interId in interventionMentionsData) {
                if (visibleInterventions.has(interId)) {
                    var mentionsArray = interventionMentionsData[interId];
                    mentionsArray.forEach(function(mention) {
                        if (mention.type === selectedType) {
                            mentionFreq[mention.text] = (mentionFreq[mention.text] || 0) + 1;
                        }
                    });
                }
            }
            var mentionData = [];
            for (var text in mentionFreq) {
                 mentionData.push({ text: text, count: mentionFreq[text] });
            }
            mentionData.sort(function(a, b) { return b.count - a.count; });
            var headerHtml = "<div style='font-size:12px; color:#333; margin:0; padding:4px; border-bottom:1px solid #ddd;'>Mentions for type: " + selectedType + "</div>";
            var tableHtml = "<div style='overflow-y:auto; max-height:550px;'><table style='width:100%; border-collapse: collapse; font-size:12px;'>" +
                            "<thead style='position:sticky; top:0; background:#fff;'><tr><th style='border:1px solid #ddd; padding:4px;'>Mention</th><th style='border:1px solid #ddd; padding:4px;'>Frequency</th></tr></thead>" +
                            "<tbody>";
            mentionData.forEach(function(d) {
                 tableHtml += "<tr><td style='border:1px solid #ddd; padding:4px;'>" + d.text + "</td><td style='border:1px solid #ddd; padding:4px; text-align:right;'>" + d.count + "</td></tr>";
            });
            tableHtml += "</tbody></table>";
            document.getElementById("mentionsTableContainer").innerHTML = headerHtml + tableHtml;
        }
        
        document.getElementById("mentionsToggle").addEventListener("change", updateMentionsView);
        updateMentionsView();
    });
    """)
    html.append("    </script>")
    html.append("  </div>")
    html.append("</body>")
    html.append("</html>")
    return "\n".join(html)

def generate_speaker_html(speaker, data):
    """Generate the HTML page for a participant."""
    topics_links = [ {"debate": info["debate_id"],
                      "intervention": info["intervention"],
                      "html": make_link(info["debate_id"], info["intervention"], f"[{info['debate_id']}] {topic} ({info['count']} {'intervention' if info['count']==1 else 'interventions'})"),
                      "full_text": info.get("full_text", "")}
                     for topic, info in data["topics"].items() ]
    proposals_links = []
    for text, values in data["proposals_texts"].items():
        if len(values) >= 3:
            debate_id, inter_id, full_text = values
        else:
            debate_id, inter_id = values
            full_text = ""
        proposals_links.append({
            "debate": debate_id,
            "intervention": inter_id,
            "html": make_link(debate_id, inter_id, f"[{debate_id}] " + text),
            "full_text": full_text
        })
    claims_links = []
    for text, values in data["claims_texts"].items():
        if len(values) >= 3:
            debate_id, inter_id, full_text = values
        else:
            debate_id, inter_id = values
            full_text = ""
        claims_links.append({
            "debate": debate_id,
            "intervention": inter_id,
            "html": make_link(debate_id, inter_id, f"[{debate_id}] " + text),
            "full_text": full_text
        })
    fallacies_links = []
    for text, values in data.get("fallacies_texts", {}).items():
        if len(values) >= 3:
            debate_id, inter_id, full_text = values
        else:
            debate_id, inter_id = values
            full_text = ""
        fallacies_links.append({
            "debate": debate_id,
            "intervention": inter_id,
            "html": make_link(debate_id, inter_id, f"[{debate_id}] " + text),
            "full_text": full_text
        })

    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html lang='en'>")
    html.append("<head>")
    html.append("  <meta charset='UTF-8'>")
    html.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html.append(f"  <title>Participant: {speaker}</title>")
    html.append("  <link href='https://fonts.googleapis.com/css?family=Roboto:400,500,700&display=swap' rel='stylesheet'>")
    html.append("  <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>")
    html.append("  <script src='https://d3js.org/d3.v6.min.js'></script>")
    html.append("  <script src='https://cdnjs.cloudflare.com/ajax/libs/d3-cloud/1.2.5/d3.layout.cloud.min.js'></script>")

    html.append("  <style>")
    html.append(""" 
      * { box-sizing: border-box; }
      body { font-family: 'Roboto', sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; color: #333; line-height: 1.6; }
      a { color: #007acc; text-decoration: none; transition: color 0.3s ease; }
      a:hover { color: #005999; text-decoration: underline; }
      h1, h2, h3 { margin: 0 0 15px; font-weight: 500; }
      header { background-color: #007acc; color: #fff; padding: 20px; text-align: center; }
      .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
      .card { background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }
      #debateFilters { position: fixed; top: 120px; right: 20px; z-index: 1000; width: 250px; }
      .frames-container { display: block; }
      .frame { margin-bottom: 20px; }
      .scroll-box { max-height: 400px; overflow-y: auto; padding: 10px; border: 1px solid #ccc; margin-top: 10px; }
      table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
      th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
      th { background-color: #007acc; color: #fff; }
      tr:nth-child(even) { background-color: #f9f9f9; }
      .emotions-container { display: flex; flex-wrap: wrap; gap: 20px; }
      .emotions-container .table-wrapper, .emotions-container .chart-wrapper { flex: 1 1 45%; max-width: 45%; }
      .chart-container { position: relative; margin: 20px auto; height: 350px; width: 350px; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 20px; }
      /* Estilos para visualización de menciones */
      #mentionsCloud, #mentionsAltContainer { min-height: 400px; }
      #mentionsAltContainer { overflow: hidden; }
      #mentionsBarChart { float: left; width: 50%; }
      #mentionsTableContainer { float: right; width: 45%; overflow-y: auto; }
      .switch {
        position: relative;
        display: inline-block;
        width: 50px;
        height: 24px;
        vertical-align: middle;
      }
      .switch input {display:none;}
      .slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: #ccc;
        transition: .4s;
        border-radius: 24px;
      }
      .slider:before {
        position: absolute;
        content: "";
        height: 18px;
        width: 18px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: .4s;
        border-radius: 50%;
      }
      input:checked + .slider {
        background-color: #007acc;
      }
      input:checked + .slider:before {
        transform: translateX(26px);
      }
      #mentionsSwitch { margin-bottom: 10px; }
      #mentionsSwitchLabel { font-size: 14px; margin-left: 8px; vertical-align: middle; }
    """)
    html.append("  </style>")
    html.append("</head>")
    html.append("<body>")
    html.append(f"  <header><h1>Participant: {speaker} ({data['party'] if data['party'] else 'No party'})</h1></header>")
    html.append("  <div class='container'>")
    html.append("    <div class='card'>")
    html.append("      <h2>Metrics</h2>")
    html.append("      <ul>")
    html.append(f"        <li><strong>Debates:</strong> {len(data['debates'])}</li>")
    html.append(f"        <li><strong>Interventions:</strong> {data['interventions']}</li>")
    html.append(f"        <li><strong>Sentences:</strong> {data['sentences']}</li>")
    html.append(f"        <li><strong>Words:</strong> {data['words']}</li>")
    html.append("      </ul>")
    html.append("      <div id='debateFilters' class='card'>")
    html.append("        <h3>Filter by Debates</h3>")
    html.append("        <div id='debateCheckboxes'>")
    html.append("          <ul>")
    for debate in sorted(data["debates"]):
        html.append(f"            <li><label><input type='checkbox' class='debateCheckbox' value='{debate}' checked> {debate}</label></li>")
    html.append("          </ul>")
    html.append("        </div>")
    html.append("        <input type='text' id='keywordFilter' placeholder='Filter by keyword'><br>")
    html.append("        <div><label><input type='checkbox' id='matchWholeWord'> Match whole word</label></div>")
    html.append("      </div>")
    html.append("      <div id='interventionEmotions' style='display:none;'>" + json.dumps(data["interventions_emotions"]) + "</div>")
    html.append("      <div class='frames-container'>")
    html.append("        <div class='frame intervention-topics'><h3>Intervention Topics</h3><div class='scroll-box'>" + generate_frames_with_links("Intervention Topics", topics_links) + "</div></div>")
    html.append("        <div class='frame'><h3>Proposals</h3><div class='scroll-box'>" + generate_frames_with_links("Proposals", proposals_links) + "</div></div>")
    html.append("        <div class='frame'><h3>Claims</h3><div class='scroll-box'>" + generate_frames_with_links("Claims", claims_links) + "</div></div>")
    html.append("        <div class='frame'><h3>Fallacies</h3><div class='scroll-box'>" + generate_frames_with_links("Fallacies", fallacies_links) + "</div></div>")
    html.append("      </div>")
    html.append("      <h3>Emotions</h3>")
    html.append("      <div class='emotions-container'>")
    html.append("         <div class='table-wrapper'>")
    html.append("             <table id='emotionTable'>")
    html.append("                <tr><th>Emotion</th><th>Sentences</th><th>Percentage</th></tr>")
    for emo, count in sorted(data["emotions"].items(), key=lambda x: x[0]):
        pct = (count / data["interventions"] * 100) if data["interventions"] else 0
        html.append(f"                <tr><td>{emo}</td><td>{count}</td><td>{pct:.1f}%</td></tr>")
    html.append("             </table>")
    html.append("         </div>")
    html.append("         <div class='chart-wrapper'>")
    html.append("             <div class='chart-container'><canvas id='emotionChart'></canvas></div>")
    html.append("         </div>")
    html.append("      </div>")
    # Sección de Mentions
    exclude_mention_types = {"DATE", "MONEY", "PERCENT", "QUANTITY", "TIME"}
    filtered_mentions = {id_intervention: [
        mention for mention in list_mentions if mention["type"] not in exclude_mention_types
    ] for id_intervention, list_mentions in data["intervention_mentions"].items()}
    html.append("      <div id='interventionMentions' style='display:none;'>" + json.dumps(filtered_mentions) + "</div>")
    html.append("      <h3>Mentions</h3>")
    html.append("      <div id='mentionsSwitch'>")
    html.append("        <label class='switch'>")
    html.append("          <input type='checkbox' id='mentionsToggle' checked>")
    html.append("          <span class='slider'></span>")
    html.append("        </label>")
    html.append("        <span id='mentionsSwitchLabel'>Frequency per type</span>")
    html.append("      </div>")
    html.append("      <div id='mentionsAltContainer' style='display:block;'>")
    html.append("          <div id='mentionsBarChart'></div>")
    html.append("          <div id='mentionsTableContainer'></div>")
    html.append("          <div style='clear:both;'></div>")
    html.append("      </div>")
    html.append("      <div id='mentionsCloudContainer' style='display:none;'>")
    html.append("          <div id='mentionsCloud'></div>")
    html.append("          <div id='mentionsLegend' style='margin-top:10px;'></div>")
    html.append("      </div>")
    html.append("      <p><a href='index.html'>← Back to index</a></p>")
    html.append("    </div>")
    html.append("    <script>")
    html.append(generate_emotion_chart_js(data["emotions"], data["interventions"], "emotionChart"))
    html.append("""
    document.addEventListener("DOMContentLoaded", function() {
        const debateCheckboxes = document.querySelectorAll("#debateCheckboxes input[type=checkbox]");
        const keywordInput = document.getElementById("keywordFilter");
        const matchWholeWordChk = document.getElementById("matchWholeWord");        
        
        function filtrarElementos() {
            let debatesSeleccionados = Array.from(debateCheckboxes)
                .filter(chk => chk.checked)
                .map(chk => chk.value);
            const keyword = keywordInput ? keywordInput.value.trim().toLowerCase() : "";
            const useWholeWord = matchWholeWordChk ? matchWholeWordChk.checked : false;
            const elementos = document.querySelectorAll(".frames-container li[data-debate][data-intervention]");
            elementos.forEach(item => {
                const debate = item.getAttribute("data-debate");
                const isInterventionTopic = item.closest('.intervention-topics') !== null;
                const textToSearch = isInterventionTopic 
                    ? (item.getAttribute("data-fulltext") || "").toLowerCase()
                    : item.textContent.toLowerCase();
                let matchesDebate = debatesSeleccionados.includes(debate);
                let matchesKeyword = true;
                if (keyword) {
                    if (useWholeWord) {
                        const words = textToSearch.match(/[\p{L}\d]+/gu);
                        matchesKeyword = words.includes(keyword);
                    } else {
                        matchesKeyword = textToSearch.includes(keyword);
                    }
                }
                item.style.display = (matchesDebate && matchesKeyword) ? "" : "none";
            });
            updateEmotions();
            updateMentionsView();
        }
        debateCheckboxes.forEach(chk => chk.addEventListener("change", filtrarElementos));
        keywordInput.addEventListener("input", filtrarElementos);
        matchWholeWordChk.addEventListener("change", filtrarElementos);        
        filtrarElementos();
    
        function updateEmotions() {
            var selectedDebates = Array.from(debateCheckboxes)
                .filter(chk => chk.checked)
                .map(chk => chk.value);
            var visibleInterventionsByDebate = {};
            document.querySelectorAll(".frames-container li[data-debate][data-intervention]:not([style*='display: none'])").forEach(function(item) {
                var debate = item.getAttribute("data-debate");
                var interId = item.getAttribute("data-intervention");
                if (selectedDebates.includes(debate)) {
                    if (!visibleInterventionsByDebate[debate]) {
                        visibleInterventionsByDebate[debate] = new Set();
                    }
                    visibleInterventionsByDebate[debate].add(interId);
                }
            });
            var interventionEmotionsData = JSON.parse(document.getElementById('interventionEmotions').innerText || '{}');
            var newEmotions = {};
            for (var debate in interventionEmotionsData) {
                if (selectedDebates.includes(debate) && visibleInterventionsByDebate[debate]) {
                    for (var interId in interventionEmotionsData[debate]) {
                        if (visibleInterventionsByDebate[debate].has(interId)) {
                            for (var emo in interventionEmotionsData[debate][interId]) {
                                newEmotions[emo] = (newEmotions[emo] || 0) + interventionEmotionsData[debate][interId][emo];
                            }
                        }
                    }
                }
            }
            var totalCount = 0;
            for (var emo in newEmotions) {
                totalCount += newEmotions[emo];
            }
            var sortedEmos = Object.keys(newEmotions).sort();
            var tableHTML = "<tr><th>Emotion</th><th>Sentences</th><th>Percentage</th></tr>";
            sortedEmos.forEach(function(emo) {
                var count = newEmotions[emo] || 0;
                var pct = totalCount > 0 ? ((count / totalCount) * 100).toFixed(1) : "0.0";
                tableHTML += "<tr><td>" + emo + "</td><td>" + count + "</td><td>" + pct + "%</td></tr>";
            });
            document.getElementById("emotionTable").innerHTML = tableHTML;
            var labels = sortedEmos;
            var dataArr = labels.map(function(emo){ return newEmotions[emo] || 0; });
            if (window.emotionChart) {
                window.emotionChart.data.labels = labels;
                window.emotionChart.data.datasets[0].data = dataArr;
                window.emotionChart.update();
            }
        }
        
        // Declarar activeMentionTypes globalmente para la Word Cloud
        var activeMentionTypes = {};

        // Función para actualizar la vista de menciones según el estado del toggle switch
        function updateMentionsView() {
            var toggle = document.getElementById("mentionsToggle");
            var switchLabel = document.getElementById("mentionsSwitchLabel");
            if (toggle.checked) {
                // Frequency per type view
                switchLabel.innerText = "Frequency per type";
                document.getElementById("mentionsAltContainer").style.display = "block";
                document.getElementById("mentionsCloudContainer").style.display = "none";
                updateAltMentions();
            } else {
                // Word cloud view
                switchLabel.innerText = "Word cloud";
                document.getElementById("mentionsAltContainer").style.display = "none";
                document.getElementById("mentionsCloudContainer").style.display = "block";
                updateCloudMentions();
            }
        }
        
        // Actualización de la Word Cloud (vista antigua)
        function updateCloudMentions() {
            var visibleInterventions = new Set();
            document.querySelectorAll(".frames-container li[data-intervention]:not([style*='display: none'])").forEach(function(item) {
                visibleInterventions.add(item.getAttribute("data-intervention"));
            });
            var interventionMentionsData = JSON.parse(document.getElementById('interventionMentions').innerText || '{}');
            var mentionsFrequency = {};
            for (var interId in interventionMentionsData) {
                if (visibleInterventions.has(interId)) {
                    var mentionsArray = interventionMentionsData[interId];
                    mentionsArray.forEach(function(mention) {
                        var key = mention.text + "|" + mention.type;
                        if (!mentionsFrequency[key]) {
                            mentionsFrequency[key] = { count: 0, text: mention.text, type: mention.type };
                        }
                        mentionsFrequency[key].count += 1;
                    });
                }
            }
            var maxCount = 0;
            var wordsData = [];
            for (var key in mentionsFrequency) {
                if (mentionsFrequency[key].count > maxCount) {
                    maxCount = mentionsFrequency[key].count;
                }
                wordsData.push(mentionsFrequency[key]);
            }
            wordsData.forEach(function(d) {
                if (!(d.type in activeMentionTypes)) {
                    activeMentionTypes[d.type] = true;
                }
            });
            var filteredWordsData = wordsData.filter(function(d) {
                return activeMentionTypes[d.type];
            });
            var fontSizeScale = d3.scaleLinear()
                                  .domain([0, maxCount])
                                  .range([12, 42]);
            var wordsForCloud = filteredWordsData.map(function(d) {
                return { text: d.text, size: fontSizeScale(d.count), type: d.type, count: d.count };
            });
            var container = d3.select("#mentionsCloud");
            container.selectAll("*").remove();
            var width = container.node().getBoundingClientRect().width;
            var height = 600;
            var uniqueTypes = Array.from(new Set(wordsData.map(function(d) { return d.type; })));
            var colorScale = d3.scaleOrdinal().domain(uniqueTypes).range(d3.schemeSet2);
            function drawCloud(words) {
                var svg = container.append("svg")
                                   .attr("width", width)
                                   .attr("height", height)
                                   .append("g")
                                   .attr("transform", "translate(" + width/2 + "," + height/2 + ")");
                var cloud = svg.selectAll("text")
                               .data(words, function(d) { return d.text; });
                cloud.enter()
                     .append("text")
                     .style("font-family", "Impact")
                     .style("fill", function(d) { return colorScale(d.type); })
                     .attr("text-anchor", "middle")
                     .attr("font-size", 1)
                     .text(function(d) { return d.text; })
                     .transition()
                     .duration(600)
                     .style("font-size", function(d) { return d.size + "px"; })
                     .attr("transform", function(d) { return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")"; })
                     .style("fill-opacity", 1);
                cloud.exit()
                     .transition()
                     .duration(200)
                     .style("fill-opacity", 1e-6)
                     .attr("font-size", 1)
                     .remove();
            }
            d3.layout.cloud().size([width, height])
                .words(wordsForCloud)
                .padding(5)
                .rotate(function() { return ~~(Math.random() * 2) * 90; })
                .font("Impact")
                .fontSize(function(d) { return d.size; })
                .on("end", drawCloud)
                .start();
                
            var legendHTML = "<p style='font-size:12px; color:#555; margin:0 0 5px 0;'>Click on each type to filter</p><strong>Legend:</strong> ";
            uniqueTypes.forEach(function(type) {
                var isActive = activeMentionTypes[type];
                var squareStyle = "width:12px; height:12px; display:inline-block; margin-right:5px; cursor:pointer;";
                if (isActive) {
                    squareStyle += "background:" + colorScale(type) + ";";
                } else {
                    squareStyle += "border: 2px solid " + colorScale(type) + ";";
                }
                legendHTML += "<span class='legend-item' data-type='" + type + "' style='cursor:pointer; margin-right:10px;'>";
                legendHTML += "<span style='" + squareStyle + "'></span>" + type + "</span>";
            });
            document.getElementById("mentionsLegend").innerHTML = legendHTML;
            document.querySelectorAll(".legend-item").forEach(function(item) {
                item.addEventListener("click", function() {
                    var type = this.getAttribute("data-type");
                    activeMentionTypes[type] = !activeMentionTypes[type];
                    updateCloudMentions();
                });
            });
        }
        
        // Actualización de la Alternative View: Bar Chart + Table (Frequency per type)
        function updateAltMentions() {
            d3.select("#mentionsBarChart").selectAll("*").remove();
            document.getElementById("mentionsTableContainer").innerHTML = "";
            var visibleInterventions = new Set();
            document.querySelectorAll(".frames-container li[data-intervention]:not([style*='display: none'])").forEach(function(item) {
                visibleInterventions.add(item.getAttribute("data-intervention"));
            });
            var interventionMentionsData = JSON.parse(document.getElementById('interventionMentions').innerText || '{}');
            var typeFrequency = {};
            for (var interId in interventionMentionsData) {
                if (visibleInterventions.has(interId)) {
                    var mentionsArray = interventionMentionsData[interId];
                    mentionsArray.forEach(function(mention) {
                        typeFrequency[mention.type] = (typeFrequency[mention.type] || 0) + 1;
                    });
                }
            }
            var dataTypes = [];
            for (var t in typeFrequency) {
                dataTypes.push({ type: t, count: typeFrequency[t] });
            }
            dataTypes.sort(function(a, b) { return b.count - a.count; });
            var chartMargin = {top: 20, right: 20, bottom: 20, left: 120};
            var chartWidth = document.getElementById("mentionsBarChart").clientWidth - chartMargin.left - chartMargin.right;
            var chartHeight = 600;
            document.getElementById("mentionsTableContainer").style.height = chartHeight + "px";
            var svg = d3.select("#mentionsBarChart")
                        .append("svg")
                        .attr("width", chartWidth + chartMargin.left + chartMargin.right)
                        .attr("height", chartHeight + chartMargin.top + chartMargin.bottom)
                        .append("g")
                        .attr("transform", "translate(" + chartMargin.left + "," + chartMargin.top + ")");
            d3.select("#mentionsBarChart").insert("p",":first-child")
              .attr("style", "font-size:12px; color:#555; margin:0 0 5px 0;")
              .text("Click on a type to see its frequencies");
            var yScale = d3.scaleBand()
                           .domain(dataTypes.map(function(d){ return d.type; }))
                           .range([0, chartHeight])
                           .padding(0.1);
            var xScale = d3.scaleLinear()
                           .domain([0, d3.max(dataTypes, function(d){ return d.count; })])
                           .range([0, chartWidth]);
            var uniqueTypes = dataTypes.map(function(d){ return d.type; });
            var colorScale = d3.scaleOrdinal().domain(uniqueTypes).range(d3.schemeSet2);
            svg.selectAll(".bar")
               .data(dataTypes)
               .enter()
               .append("rect")
               .attr("class", "bar")
               .attr("y", function(d){ return yScale(d.type); })
               .attr("height", yScale.bandwidth())
               .attr("x", 0)
               .attr("width", function(d){ return xScale(d.count); })
               .attr("fill", function(d){ return colorScale(d.type); })
               .style("cursor", "pointer")
               .on("click", function(event, d) {
                    updateMentionsTable(d.type);
               });
            svg.selectAll(".label")
               .data(dataTypes)
               .enter()
               .append("text")
               .attr("class", "label")
               .attr("x", -10)
               .attr("y", function(d){ return yScale(d.type) + yScale.bandwidth()/2; })
               .attr("dy", ".35em")
               .attr("text-anchor", "end")
               .style("font-size", "11px")
               .text(function(d){ return d.type; })
               .style("cursor", "pointer")
               .on("click", function(event, d) {
                    updateMentionsTable(d.type);
               });
            if (dataTypes.length > 0) {
                 updateMentionsTable(dataTypes[0].type);
            }
        }
        
        // Función para actualizar la tabla de la Alternative View con encabezado fijo (thead sticky)
        function updateMentionsTable(selectedType) {
            var visibleInterventions = new Set();
            document.querySelectorAll(".frames-container li[data-intervention]:not([style*='display: none'])").forEach(function(item) {
                visibleInterventions.add(item.getAttribute("data-intervention"));
            });
            var interventionMentionsData = JSON.parse(document.getElementById('interventionMentions').innerText || '{}');
            var mentionFreq = {};
            for (var interId in interventionMentionsData) {
                if (visibleInterventions.has(interId)) {
                    var mentionsArray = interventionMentionsData[interId];
                    mentionsArray.forEach(function(mention) {
                        if (mention.type === selectedType) {
                            mentionFreq[mention.text] = (mentionFreq[mention.text] || 0) + 1;
                        }
                    });
                }
            }
            var mentionData = [];
            for (var text in mentionFreq) {
                 mentionData.push({ text: text, count: mentionFreq[text] });
            }
            mentionData.sort(function(a, b) { return b.count - a.count; });
            var headerHtml = "<div style='font-size:12px; color:#333; margin:0; padding:4px; border-bottom:1px solid #ddd;'>Mentions for type: " + selectedType + "</div>";
            var tableHtml = "<div style='overflow-y:auto; max-height:550px;'><table style='width:100%; border-collapse: collapse; font-size:12px;'>" +
                            "<thead style='position:sticky; top:0; background:#fff;'><tr><th style='border:1px solid #ddd; padding:4px;'>Mention</th><th style='border:1px solid #ddd; padding:4px;'>Frequency</th></tr></thead>" +
                            "<tbody>";
            mentionData.forEach(function(d) {
                 tableHtml += "<tr><td style='border:1px solid #ddd; padding:4px;'>" + d.text + "</td><td style='border:1px solid #ddd; padding:4px; text-align:right;'>" + d.count + "</td></tr>";
            });
            tableHtml += "</tbody></table>";
            document.getElementById("mentionsTableContainer").innerHTML = headerHtml + tableHtml;
        }
        
        document.getElementById("mentionsToggle").addEventListener("change", updateMentionsView);
        updateMentionsView();
    });
    """)
    html.append("    </script>")
    html.append("  </div>")
    html.append("</body>")
    html.append("</html>")
    return "\n".join(html)

def generate_index_html(global_metrics, speaker_metrics, party_metrics):
    """Generate the index.html page with global metrics and sections for debates, parties, and participants."""
    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html lang='en'>")
    html.append("<head>")
    html.append("  <meta charset='UTF-8'>")
    html.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html.append("  <title>DebatES Interactive Reports - Index</title>")
    html.append("  <link href='https://fonts.googleapis.com/css?family=Roboto:400,500,700&display=swap' rel='stylesheet'>")
    html.append("  <style>")
    html.append(""" 
      * { box-sizing: border-box; }
      body { font-family: 'Roboto', sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; color: #333; line-height: 1.6; }
      a { color: #007acc; text-decoration: none; transition: color 0.3s ease; }
      a:hover { color: #005999; text-decoration: underline; }
      h1, h2, h3 { margin: 0 0 15px; font-weight: 500; }
      header { background-color: #007acc; color: #fff; padding: 20px; text-align: center; }
      .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
      .card { background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }
      .debates-grid, .parties-grid, .participants-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
      .debate-card, .party-card, .participant-card { background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 15px; }
      .debate-card h3, .party-card h3, .participant-card h3 { margin: 0 0 10px; font-size: 1.2em; }
      .debate-card ul, .party-card ul, .participant-card ul { list-style: none; padding: 0; margin: 0; font-size: 0.9em; }
      .debate-card li, .party-card li, .participant-card li { margin: 2px 0; }
    """)
    html.append("  </style>")
    html.append("</head>")
    html.append("<body>")
    html.append("  <header><h1>DebatES Interactive Reports</h1></header>")
    html.append("  <div class='container'>")
    html.append("    <div class='card'>")
    html.append("      <h2>Global Metrics</h2>")
    html.append("      <ul>")
    html.append(f"        <li><strong>Processed Debates:</strong> {global_metrics['debates']}</li>")
    html.append(f"        <li><strong>Total Blocks:</strong> {global_metrics['blocks']}</li>")
    html.append(f"        <li><strong>Total Interventions:</strong> {global_metrics['interventions']}</li>")
    html.append(f"        <li><strong>Total Sentences:</strong> {global_metrics['sentences']}</li>")
    html.append(f"        <li><strong>Total Words:</strong> {global_metrics['words']}</li>")
    total = 0
    for _, metrics in global_metrics["debates_info"].items():
        total += sum(len(mentions) for mentions in metrics["intervention_mentions"].values())
    html.append(f"        <li><strong>Total Mentions:</strong> {total}</li>")
    html.append("      </ul>")
    html.append("    </div>")
    html.append("    <div class='card'>")
    html.append("      <h2>Reports by debate</h2>")
    html.append("      <details>")
    html.append("        <summary>Click to open/close</summary>")
    html.append("      <div class='debates-grid'>")
    if "debates_info" in global_metrics:
        for debate_id, info in sorted(global_metrics["debates_info"].items(), key=lambda x: x[0]):
            filename = f"debate_{sanitize_filename(debate_id)}.html"
            display = f"{info['date']}"
            html.append("        <div class='debate-card'>")
            html.append(f"          <h3><a href='{filename}'>{display}</a></h3>")
            html.append("          <ul>")
            for speaker in info.get("speakers", []):
                if speaker not in ["MODERADOR", "DECLARACIONES"]:
                    party = speaker_metrics.get(speaker, {}).get("party", "No party")
                    html.append(f"            <li>{speaker} ({party})</li>")
            html.append("          </ul>")
            html.append("        </div>")
    html.append("      </div>")
    html.append("    </details>")
    html.append("    </div>")
    html.append("    <div class='card'>")
    html.append("      <h2>Reports by political party</h2>")
    html.append("      <details>")
    html.append("        <summary>Click to open/close</summary>")
    html.append("      <div class='parties-grid'>")
    for party, data in sorted(party_metrics.items()):
        if party != "No party":
            filename = f"party_{sanitize_filename(party)}.html"
            html.append("        <div class='party-card'>")
            html.append(f"          <h3><a href='{filename}'>{party}</a></h3>")
            html.append("          <ul>")
            html.append(f"            <li><strong>Debates:</strong> {len(data['debates'])}</li>")
            html.append(f"            <li><strong>Participants:</strong> {len(data['participants'])}</li>")
            html.append(f"            <li><strong>Interventions:</strong> {data['interventions']}</li>")
            html.append(f"            <li><strong>Sentences:</strong> {data['sentences']}</li>")
            html.append(f"            <li><strong>Words:</strong> {data['words']}</li>")
            html.append("          </ul>")
            html.append("        </div>")
    html.append("      </div>")
    html.append("    </details>")
    html.append("    </div>")
    html.append("    <div class='card'>")
    html.append("      <h2>Reports by participants</h2>")
    html.append("      <details>")
    html.append("        <summary>Click to open/close</summary>")
    html.append("      <div class='participants-grid'>")
    for speaker, data in sorted(speaker_metrics.items()):
        if speaker not in ["MODERADOR", "DECLARACIONES"]:
            filename = f"speaker_{sanitize_filename(speaker)}.html"
            html.append("        <div class='participant-card'>")
            html.append(f"          <h3><a href='{filename}'>{speaker}</a></h3>")
            html.append("          <ul>")
            html.append(f"            <li><strong>Party:</strong> {data.get('party', 'No party')}</li>")
            html.append(f"            <li><strong>Debates:</strong> {len(data.get('debates', []))}</li>")
            html.append(f"            <li><strong>Interventions:</strong> {data.get('interventions', 0)}</li>")
            html.append(f"            <li><strong>Sentences:</strong> {data.get('sentences', 0)}</li>")
            html.append(f"            <li><strong>Words:</strong> {data.get('words', 0)}</li>")
            html.append("          </ul>")
            html.append("        </div>")
    html.append("      </div>")
    html.append("    </details>")
    html.append("    </div>")
    html.append("  </div>")
    html.append("</body>")
    html.append("</html>")
    return "\n".join(html)

def main(directory):
    # Initialize global, speaker and party metrics structures
    global global_metrics  # For use in generate_debate_html
    global_metrics = {
        "debates": 0,
        "blocks": 0,
        "interventions": 0,
        "sentences": 0,
        "words": 0,
        "claims": 0,
        "proposals": 0,
        "fallacies": 0,                
        "sentence_lengths": [],
        "sentences_per_intervention": [],
        "intervention_word_counts": [],
        "block_topics": defaultdict(int),
        "intervention_topics": defaultdict(int),
        "emotions": defaultdict(int),
        "debates_info": {}
    }
    speaker_metrics = {}  # Key: full-name
    party_metrics = {}

    # Create output folder
    output_dir = "html"
    os.makedirs(output_dir, exist_ok=True)

    # Walk through the directory looking for XML files
    for root_dir, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".xml"):
                file_path = os.path.join(root_dir, file)
                print(f"Processing {file_path}...")
                debate_id = process_xml(file_path, global_metrics, speaker_metrics, party_metrics)
                if debate_id:
                    transcription_html = parse_xml_to_transcription_html(file_path)
                    transcription_filename = f"debate_{sanitize_filename(debate_id)}_transcription.html"
                    with open(os.path.join(output_dir, transcription_filename), "w", encoding="utf-8") as f:
                        f.write(transcription_html)

    # Generate index.html
    index_html = generate_index_html(global_metrics, speaker_metrics, party_metrics)
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # Generate page for each speaker
    for speaker, data in speaker_metrics.items():
        filename = f"speaker_{sanitize_filename(speaker)}.html"
        content = generate_speaker_html(speaker, data)
        with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)

    # Generate page for each party
    for party, data in party_metrics.items():
        filename = f"party_{sanitize_filename(party)}.html"
        content = generate_party_html(party, data)
        with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)

    # Generate page for each debate
    if "debates_info" in global_metrics:
        for debate_id, data in global_metrics["debates_info"].items():
            filename = f"debate_{sanitize_filename(debate_id)}.html"
            content = generate_debate_html(debate_id, data)
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                f.write(content)

    print(f"\nHTML report generated in the '{output_dir}' folder.")

if __name__ == "__main__":    
    main("xml")
