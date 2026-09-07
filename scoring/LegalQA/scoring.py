import json
import os
import numpy as np
import nltk 

from nltk.translate.meteor_score import meteor_score
# from pyvi import ViTokenizer
from rouge_score import rouge_scorer

nltk.download('wordnet')
nltk.download('omw-1.4')

reference_dir = os.path.join('/app/input', 'ref')
prediction_dir = os.path.join('/app/input', 'res')
score_dir = '/app/output'


def read_json(file):
    with open(file, encoding="utf8") as f:
        return json.load(f)
    f.close()

def eval_qa(y_pred, y_true):
    rouge_scoring = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=False)

    def build_in_tokenizer(string_sent):
        # Dung pyvi cho tokenizer 
        # return ViTokenizer.tokenize(str(string_sent))
        
        # Khong dung Tokenizer 
        return string_sent

    try:
        y_pred = {k : v['answer'] for k, v in y_pred.items()}
        
        ids_preds = []
        ids_truth = []
        for k, v in y_pred.items():
            ids_preds.append(k)

        for k, v in y_true.items():
            ids_truth.append(k)

        if len(ids_preds) != len(ids_truth):
            print("Samples in predict not match with reference")
            raise Exception

        rouge_result = np.array([rouge_scoring.score(build_in_tokenizer(str(y_true[k])), build_in_tokenizer(str(y_pred[k])))['rougeL'].fmeasure for k in ids_preds]).mean()
        print(rouge_result)
        meteor_result = np.array([meteor_score([build_in_tokenizer(str(y_true[k])).split()], build_in_tokenizer(str(y_pred[k])).split()) for k in ids_preds]).mean()
        print(meteor_result)
        return {'rouge': rouge_result, 'meteor': meteor_result}
    except Exception as e:
        print(e)
        raise e
        # return {'rouge': 0.0, 'meteor': 0.0}


def main():
    scores = {'rouge': 0.0, 'meteor': 0.0}

    metadata = read_json(os.path.join(reference_dir, 'metadata.json'))
    truth = read_json(os.path.join(reference_dir, metadata['files']['reference']))

    if metadata['files'].get('input'):
        input_data = read_json(os.path.join(prediction_dir, metadata['files']['input']))
        eval_scores = eval_qa(input_data, truth)
        scores.update(eval_scores)
    else:
        print("Input file name not correct. ")
        raise Exception

    print("Final scores:", scores)

    with open(os.path.join(score_dir, 'scores.json'), 'w') as score_file:
        score_file.write(json.dumps(scores))
    score_file.close()
    
    return 0

if __name__ == "__main__": 
    exit(main())
    # pass
        