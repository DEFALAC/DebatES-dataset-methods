# DebatES dataset: methods
Code for the automatic annotation of a dataset of electoral debate transcripts in Spain.

The process for obtaining the final resource consists of the following steps:

* Run `vttc_to_segments_csv.py` to create the segment files in CSV format, containing information about the participants in each debate and linguistic analysis. This step starts from the debate transcriptions, which were obtained using WhisperX and later manually corrected (vttc files).  A serie of files are generates in the `transcriptions/segments` folder.
* Run `identify_blocks.py`, `identify_topics.py`, `extract_proposals.py`, `extract_claims.py`, and `extract_mentions.py` (in any order) to generate different types of annotations using language models. A series of files are generated in the `annotations` folder. The outputs corresponding to blocks, proposals, claims, and mentions were manually reviewed to correct errors.  
* Run `compile_xml.py` to generate one XML file per debate, compiling the transcriptions and the previously generated annotations.  
* Run `classify_emotions.py` to add emotion-related information to the sentences in the previously generated XML files.  
* Run `generate_html_reports.py` to obtain interactive reports in HTML format.  

Manual annotations of fallacies were added to the final resource.
