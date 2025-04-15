'''
This script provides functions to analyze Spanish text using SpaCy,
extract linguistic features, and compute various metrics related to lexical, syntactic, and stylistic complexity.
'''

import json
import spacy
import pandas as pd

# You need to have the Spanish model installed. You can do this with:
# python -m spacy download es_dep_news_trf

NLP_SPACY = spacy.load("es_dep_news_trf")

def analyze_text(text):
    """
    Analyzes a text using SpaCy and returns structured sentence-level information.
    Args:
        text (str): The text to be analyzed.
    Returns:
        dict: A dictionary containing:
            - "sentences_info" (list): A list of dictionaries, each containing information about a sentence:
                - "sentence_text" (str): The sentence text.
                - "tokens" (list): A list of dictionaries, each containing information about a token in the sentence:
                    - "index" (int): The token's index in the sentence.
                    - "text" (str): The token text.
                    - "lemma" (str): The token lemma.
                    - "pos" (str): The part of speech of the token.
                    - "dep_head_index" (int): The index of the token’s syntactic head.
                    - "dep_head_text" (str): The text of the syntactic head.
                    - "dep_relation" (str): The syntactic dependency relation.
                    - "is_stop" (bool): Whether the token is a stop word.
                    - "is_alpha" (bool): Whether the token is alphabetic.
            - "dep_htmls" (list): A list of HTML strings representing dependency parsing for each sentence.
    """
    doc = NLP_SPACY(text)

    sentences_info = []
    dep_htmls = []
    for sent in doc.sents:
        html_dep = spacy.displacy.render(sent, style="dep")

        sentence_data = {
            "sentence_text": sent.text,
            "tokens": [
                {
                    "index": token.i,
                    "text": token.text,
                    "lemma": token.lemma_,
                    "pos": token.pos_,                                        
                    "dep_head_index": token.head.i,
                    "dep_head_text": token.head.text,
                    "dep_relation": token.dep_,
                    "is_stop": token.is_stop,
                    "is_alpha": token.is_alpha                    
                }
                for token in sent
            ]     
        }
        sentences_info.append(sentence_data)
        dep_htmls.append(html_dep)

    return {"sentences_info": sentences_info, "dep_htmls": dep_htmls}

def _compute_metrics(df):    
    """
    Helper function that computes linguistic metrics from a DataFrame.

    Args:
        df (pandas.DataFrame): A DataFrame containing token-level information,
                               including part-of-speech tags, lemmatization, and dependency info.

    Returns:
        dict: A dictionary containing the following metrics:
            - "TTR" (float): Type-token ratio.
            - "STOP_RATIO" (float): Percentage of stop words.
            - "AVG_SENT_LEN" (float): Average sentence length in tokens.
            - "AVG_DEP_PER_VERB" (float): Average number of dependents per verb.
            - "PUNCT_RATIO" (float): Percentage of punctuation tokens.
            - "ADJ_RATIO" (float): Percentage of adjectives.
            - "ADV_RATIO" (float): Percentage of adverbs.
            - "AVG_DEP_DIST" (float): Average dependency distance.
    """
    total_tokens = len(df)
    num_sentences = df['sentence_index'].nunique()
    
    metrics = {
        "TTR": df['lemma'].nunique() / total_tokens,
        "STOP_RATIO": df['is_stop'].mean() * 100,
        "AVG_SENT_LEN": total_tokens / num_sentences,
        "AVG_DEP_PER_VERB": df[df['pos'] == 'VERB']['dep_head_index'].value_counts().mean(),
        "PUNCT_RATIO": df[df['pos'] == 'PUNCT'].shape[0] / total_tokens * 100,
        "ADJ_RATIO": df[df['pos'] == 'ADJ'].shape[0] / total_tokens * 100,
        "ADV_RATIO": df[df['pos'] == 'ADV'].shape[0] / total_tokens * 100,
    }
    
    df['dependency_distance'] = abs(df['index'] - df['dep_head_index'])
    metrics["AVG_DEP_DIST"] = df['dependency_distance'].mean()
    
    return metrics

def calculate_metrics(data):
    """
    Calculates lexical, syntactic, and stylistic complexity metrics.
    Receives the output of analyze_text() directly.

    Args:
        data (dict): Dictionary returned by analyze_text(), containing sentence and token-level info.

    Returns:
        dict: A dictionary with linguistic complexity metrics (see _compute_metrics for details).

    """
    tokens = []
    sentence_index = 0
    
    for sentence in data["sentences_info"]:
        for token in sentence["tokens"]:
            token["sentence_index"] = sentence_index
            tokens.append(token)
        sentence_index += 1
    
    df = pd.DataFrame(tokens)
    return _compute_metrics(df)

def calculate_metrics_from_list(data_list):
    """
    Calculates lexical, syntactic, and stylistic complexity metrics for multiple texts.
    Receives a list of outputs from analyze_text().

    Args:
        data_list (list): A list of dictionaries, each returned by analyze_text().

    Returns:
        dict: A dictionary with aggregated linguistic complexity metrics (see _compute_metrics for details).
    """
    tokens = []
    sentence_index = 0
    
    for data in data_list:
        for sentence in data["sentences_info"]:
            for token in sentence["tokens"]:
                token["sentence_index"] = sentence_index
                tokens.append(token)
            sentence_index += 1
    
    df = pd.DataFrame(tokens)
    return _compute_metrics(df)

# Example usage
if __name__ == "__main__":
    text = "Gracias, señor Aznar. Tiempo ahora para el candidato del Partido Socialista, Felipe González. La misma cuestión al comenzar este debate. Su idea de España. ¿Qué hace para este país? ¿A dónde vamos?"
    text2 = "Aquí otro texto más. Sólo por probar la nueva función que calcula las métricas desde una lista"

    info = analyze_text(text)
    print(json.dumps(info, indent=2, ensure_ascii=False)) 

    metrics = calculate_metrics(info)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))

    info2 = analyze_text(text2)
    lista = [info, info2]
    metrics2 = calculate_metrics_from_list(lista)
    print(json.dumps(metrics2, indent=2, ensure_ascii=False))







