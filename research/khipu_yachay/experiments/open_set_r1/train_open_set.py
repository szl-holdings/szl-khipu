# SPDX-License-Identifier: Apache-2.0
"""Khipu Yachay Open-Set R1 — original synthetic CPU training experiment.

This does not train on historic Khipu observations, Quechua speech, museum
imagery, paper text or old evaluation fixtures. It trains a small six-class
TF-IDF/logistic router in isolation and writes JSON weights (never pickle).
No model promotion, cloud job, GPU allocation or runtime route is enabled.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
LABELS=("NUMERACY","RECORDS","RESEARCH_LIMITS","DATA_RIGHTS","METHODS")
OOD="OUT_OF_SCOPE"
PATTERN=r"(?u)\b\w+\b"
THRESHOLDS=(.35,.40,.45,.50,.55,.60,.65,.70,.75,.80,.85,.90,.95)
MAX_BYTES=2_000_000
# Distinct original synthetic training and internal-development topics, not
# archaeological records or the historical/previous diagnostic challenge.
TRAIN_TOPICS=(
    "ceramic glazing","classical guitar tuning","rainforest ecology",
    "urban composting","low sodium cooking","tennis racket strings",
    "electric bus design","bicycle tire inflation","marine biology lectures",
    "music theory exercises","plant seed germination","aircraft lift physics",
    "digital camera exposure","car battery charging","volcanic rock types",
    "mountain hiking maps","solar power planning","weather radar basics",
    "printer cartridge selection","coffee bean roasting","aquarium filtration",
    "city bicycle infrastructure","garden tomato diseases","woodworking tools",
    "wireless network routers","film editing techniques","astronomy telescopes",
    "river water chemistry","motorcycle engine cooling","winter road maintenance",
    "football team formations","swimming stroke practice","home insulation",
    "marine currents","city train schedules","electronics soldering",
    "table tennis tactics","bread fermentation","language learning flashcards",
    "digital typography")
DEV_TOPICS=(
    "recycling old computers","metal bridge corrosion","acoustic piano repair",
    "sustainable wool clothing","family vacation planning","light pollution",
    "home aquarium plants","food delivery logistics","ceramic sculpture history",
    "snowboard equipment","woodwind instrument reeds","mobile app accessibility")
OOD_TEMPLATES=(
    "What are the practical basics of {}?",
    "Could you explain {} to a beginner?",
    "What equipment is needed for {}?",
    "Can you compare methods for {}?",
    "Give a useful overview of {}.",
    "How would someone study {}?",
)

def canon(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,
                       separators=(",",":"),allow_nan=False)+"\n").encode("utf-8")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def original_rows(path):
    raw=path.read_bytes()
    if len(raw)>240_000 or b"\r\n" in raw:
        raise ValueError("INPUT_NOT_CANONICAL")
    ids=set(); rows=[]
    for rawrow in raw.splitlines():
        r=json.loads(rawrow)
        if type(r) is not dict or set(r)!={"id","text","label","data_class","template_family"}:
            raise ValueError("TRAIN_SCHEMA")
        if (r["label"] not in LABELS or r["data_class"]!="SYNTHETIC_SZL_AUTHORED"
                or r["id"] in ids):
            raise ValueError("TRAIN_RIGHTS_OR_DUPLICATE")
        ids.add(r["id"]);rows.append(r)
    if len(rows)!=540:
        raise ValueError("TRAIN_N")
    return rows,sha(raw)

def negatives(topics,split):
    return [{"id":f"{split}:ood:{i}:{j}",
             "text":tmpl.format(topic),"label":OOD,
             "data_class":"ORIGINAL_SYNTHETIC_NEGATIVE",
             "template_family":f"{split}:ood:{j}"}
            for i,topic in enumerate(topics)
            for j,tmpl in enumerate(OOD_TEMPLATES)]

def candidate_data(project):
    orig,source_sha=original_rows(project/"data/synthetic_train.jsonl")
    train=[r for r in orig if r["template_family"].split(":")[-1]!="8"]
    dev=[r for r in orig if r["template_family"].split(":")[-1]=="8"]
    if len(train)!=480 or len(dev)!=60:
        raise ValueError("FAMILY_SPLIT")
    train+=negatives(TRAIN_TOPICS,"train")
    dev+=negatives(DEV_TOPICS,"dev")
    if len(train)!=720 or len(dev)!=132:
        raise ValueError("SPLIT_COUNTS")
    if {r["text"] for r in train}&{r["text"] for r in dev}:
        raise ValueError("SPLIT_OVERLAP")
    return train,dev,{"pinned_source_sha256":source_sha,
                      "train_n":len(train),"dev_n":len(dev),
                      "train_negative_n":240,"dev_negative_n":72,
                      "train_rows_sha256":sha(b"".join(canon(r) for r in train)),
                      "dev_rows_sha256":sha(b"".join(canon(r) for r in dev)),
                      "archaeological_samples_used":0,
                      "source_class":"FIRST_PARTY_SYNTHETIC_ONLY"}

def model_json(vectorizer,classifier,threshold,inputs):
    return {
        "schema":"szl.khipu-yachay.open-set-router/v1",
        "algorithm":"WORD_BIGRAM_TFIDF_MULTINOMIAL_LOGISTIC",
        "classes":[str(x) for x in classifier.classes_],
        "features":vectorizer.get_feature_names_out().tolist(),
        "idf":[float(x) for x in vectorizer.idf_],
        "weights":[[float(x) for x in row] for row in classifier.coef_],
        "bias":[float(x) for x in classifier.intercept_],
        "token_pattern":PATTERN,
        "ngram_range":[1,2],"decision_threshold":threshold,
        "training_sha256":inputs["train_rows_sha256"],
        "historical_training":False,
        "weight_identity":"RESEARCH_CANDIDATE_NOT_QUALIFIED",
        "runtime":"STDLIB_ONLY","production_qualified":False,
    }

def predict(text,model):
    """Pure stdlib inference; never import or deserialize sklearn pickles."""
    if type(text) is not str or not 1<=len(text)<=500:
        raise ValueError("QUERY_LENGTH")
    if model.get("schema")!="szl.khipu-yachay.open-set-router/v1":
        raise ValueError("MODEL_SCHEMA")
    toks=re.findall(PATTERN,text.lower())
    counter=Counter(toks)
    counter.update(toks[i]+" "+toks[i+1] for i in range(len(toks)-1))
    vocab={name:i for i,name in enumerate(model["features"])}
    features=[(vocab[k],n*model["idf"][vocab[k]])
              for k,n in counter.items() if k in vocab]
    length=math.sqrt(sum(value*value for _,value in features))
    if length==0:
        return {"intent":"ABSTAIN","reason":"NO_VOCAB_OVERLAP","prob":None}
    logits=[bias+sum(row[i]*v/length for i,v in features)
            for row,bias in zip(model["weights"],model["bias"])]
    offset=max(logits)
    exps=[math.exp(x-offset) for x in logits]
    denom=sum(exps);probs=[x/denom for x in exps]
    idx=max(range(len(probs)),key=lambda n:probs[n])
    cls=model["classes"][idx];p=probs[idx]
    cause="OOD_CLASS" if cls==OOD else (
          "LOW_PROBABILITY" if p<model["decision_threshold"] else "CLASSIFIED")
    return {"intent":cls if cause=="CLASSIFIED" else "ABSTAIN",
            "reason":cause,"prob":p}

def metrics(model,rows):
    preds=[(r["label"],predict(r["text"],model)["intent"]) for r in rows]
    inside=[x for x in preds if x[0]!=OOD]
    outside=[x for x in preds if x[0]==OOD]
    in_correct=sum(a==b for a,b in inside)
    bad=sum(b!="ABSTAIN" for _,b in outside)
    return {"in_n":len(inside),"in_correct":in_correct,
            "in_accuracy":in_correct/len(inside),
            "in_abstain":sum(b=="ABSTAIN" for _,b in inside),
            "ood_n":len(outside),"ood_false_accept":bad,
            "ood_false_accept_rate":bad/len(outside)}

def train(project,out,git_sha):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    import sklearn
    if out.exists():
        raise ValueError("OUTPUT_EXISTS")
    train,dev,inputs=candidate_data(project)
    plan={"schema":"szl.yachay.open-set.pretraining-plan/v1",
          "started_utc":datetime.now(timezone.utc).isoformat(),
          "git_sha":git_sha,"rights":"FIRST_PARTY_SYNTHETIC_ONLY",
          "excluded":["synthetic_eval.jsonl","posthoc_ood_v0.jsonl","historical_cord_content"],
          "inputs":inputs,"model":"logistic_tfidf_word_bigram",
          "fixed_seed":20261117,"candidate_C":2.0,
          "thresholds":THRESHOLDS,"train_count":len(train),
          "max_model_bytes":MAX_BYTES,
          "acceptance":{"min_dev_intent_accuracy":.55,"max_dev_ood_false_accept":.10},
          "no_paid_jobs":True,"no_model_promotion":True}
    intent=out.parent/"train-intent.json"
    with intent.open("xb") as f:
        f.write(canon(plan));f.flush();os.fsync(f.fileno())
    vec=TfidfVectorizer(token_pattern=PATTERN,ngram_range=(1,2),
                        max_features=5000,norm="l2",smooth_idf=True)
    X=vec.fit_transform([row["text"] for row in train])
    clf=LogisticRegression(C=2.0,random_state=20261117,
                            class_weight="balanced",max_iter=400,tol=1e-5)
    clf.fit(X,[row["label"] for row in train])
    choices=[]
    for t in THRESHOLDS:
        candidate=model_json(vec,clf,t,inputs)
        score=metrics(candidate,dev)
        allowed=score["in_accuracy"]>=.55 and score["ood_false_accept_rate"]<=.10
        choices.append((t,allowed,score))
    pool=[x for x in choices if x[1]] or choices
    # Disallow "abstain everywhere" as an apparent success.
    choice=max(pool,key=lambda x:(x[2]["in_correct"]-2*x[2]["ood_false_accept"],
                                  x[2]["in_correct"],-x[0]))
    t,gate,dev_score=choice
    artifact=model_json(vec,clf,t,inputs)
    if len(artifact["classes"])!=6:
        raise ValueError("MODEL_CLASSES")
    # Verify stdlib probabilities are consistent with the training library.
    probes=[r["text"] for r in train[:30]+dev]
    ref=clf.predict_proba(vec.transform(probes))
    for question,row in zip(probes,ref):
        p=predict(question,artifact)["prob"]
        if p is None or abs(p-max(row))>1e-8:
            raise RuntimeError("INFERENCE_PARITY_FAILED")
    payload=canon(artifact)
    if len(payload)>MAX_BYTES:
        raise ValueError("MODEL_LIMIT")
    out.mkdir(exist_ok=False)
    model_file=out/"candidate_model.json"
    with model_file.open("xb") as f:
        f.write(payload);f.flush();os.fsync(f.fileno())
    report={"schema":"szl.yachay.open-set.train-receipt/v1",
            "ended_utc":datetime.now(timezone.utc).isoformat(),
            "status":"TRAINED_RESEARCH_CANDIDATE",
            "source_git_sha":git_sha,
            "trained_model_sha256":sha(payload),
            "trained_model_bytes":len(payload),
            "class_count":6,"feature_count":len(artifact["features"]),
            "scikit_learn_version":sklearn.__version__,
            "optimizer_iterations":int(clf.n_iter_[0]),
            "fixed_source_training_inputs":inputs,
            "internal_dev":dev_score,"threshold":t,
            "threshold_candidates":[{"threshold":c,"meets_both":q,
                       "in_correct":m["in_correct"],"ood_false_accept":m["ood_false_accept"]}
                      for c,q,m in choices],
            "development_gate_pass":gate,
            "historical_training":False,"gpu_hours":0,"paid_jobs":0,
            "model_weights_published":False,"production_qualified":False,
            "heldout_reported_as_independent":False,
            "decision":"DEVELOPMENT_ONLY" if gate else "HOLD"}
    data=canon(report)
    with (out/"training_receipt.json").open("xb") as f:
        f.write(data);f.flush();os.fsync(f.fileno())
    return report

if __name__=="__main__":
    output=Path(sys.argv[1]).resolve()
    base_sha=sys.argv[2]
    row=train(ROOT,output,base_sha)
    print(json.dumps({"state":row["status"],
        "training_inputs":row["fixed_source_training_inputs"],
        "dev":row["internal_dev"],"threshold":row["threshold"],
        "acceptance":row["decision"],
        "model_sha256":row["trained_model_sha256"],
        "optimizer_iterations":row["optimizer_iterations"],
        "model_output_dir":str(output),"paid_jobs":0},sort_keys=True),flush=True)
