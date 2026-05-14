from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from pydantic import BaseModel
from transformers import BertTokenizer, BertModel
import torch
import torch.nn as nn
import torch.nn.functional as F
import os, json, logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

MODEL_DIR = "/Users/ananya/development/optimal_hire/model/siamese_bert_model"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

with open(os.path.join(MODEL_DIR, "config.json")) as f:
    CONFIG = json.load(f)
MAX_LENGTH = CONFIG["max_length"]
tokenizer = BertTokenizer.from_pretrained(os.path.join(MODEL_DIR, "bert"))

class SiameseBERT(nn.Module):
    def __init__(self, bert_dir):
        super().__init__()
        self.bert = BertModel.from_pretrained(bert_dir)
        self.fc = nn.Linear(768, 128)

    def encode(self, ids, mask):
        output = self.bert(input_ids=ids, attention_mask=mask)
        hidden = output.last_hidden_state
        mask = mask.unsqueeze(-1).float()
        mean_emb = (hidden * mask).sum(dim=1) / mask.sum(dim=1)
        x = self.fc(mean_emb)
        return F.normalize(x, p=2, dim=1)

    def forward(self, jd_ids, jd_mask, res_ids, res_mask):
        jd_emb = self.encode(jd_ids, jd_mask)
        res_emb = self.encode(res_ids, res_mask)
        sim = (jd_emb * res_emb).sum(dim=1)
        return sim

model = SiameseBERT(os.path.join(MODEL_DIR, "bert"))
model.load_state_dict(torch.load(
    os.path.join(MODEL_DIR, "siamese_bert_weights.pt"),
    map_location=DEVICE
))
model.to(DEVICE)
model.eval()

def score_match(job_desc: str, resume: str) -> float:
    jd_tokens = tokenizer(job_desc, max_length=MAX_LENGTH, padding="max_length",
                          truncation=True, return_tensors="pt")
    res_tokens = tokenizer(resume, max_length=MAX_LENGTH, padding="max_length",
                           truncation=True, return_tensors="pt")
    jd_ids, jd_mask = jd_tokens["input_ids"].to(DEVICE), jd_tokens["attention_mask"].to(DEVICE)
    res_ids, res_mask = res_tokens["input_ids"].to(DEVICE), res_tokens["attention_mask"].to(DEVICE)

    with torch.no_grad():
        sim = model(jd_ids, jd_mask, res_ids, res_mask)
    return round((sim.item() + 1) / 2, 3)

JOBS = [
    "Software engineer with Python and Django experience.",
    "Data scientist skilled in machine learning and pandas.",
    "Frontend developer using React and JavaScript."
]

RESUMES = [
    "Python developer with Django and REST APIs.",
    "Worked on ML projects with pandas and scikit-learn.",
    "Frontend engineer experienced in React and CSS."
]

class JobInput(BaseModel):
    job_description: str

class ResumeInput(BaseModel):
    resume: str

@app.route("/score_resumes_for_job", methods=["POST"])
def score_resumes_for_job():
    """Given a job description, return matching resumes."""
    try:
        data = request.get_json()
        if not data or "job_description" not in data:
            return jsonify({"error": "Missing 'job_description' field"}), 400
        job_description = data["job_description"]
        matches = [
            {"resume": r, "score": score_match(job_description, r)}
            for r in RESUMES
        ]
        matches.sort(key=lambda x: x["score"], reverse=True)
        return jsonify({
            "job_description": job_description,
            "matches": matches
        }), 200
    except Exception as e:
        logger.exception(f"Error in score_resumes_for_job: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route("/score_jobs_for_resume", methods=["POST"])
def score_jobs_for_resume():
    """Given a resume, return matching job descriptions."""
    try:
        data = request.get_json()
        if not data or "resume" not in data:
            return jsonify({"error": "Missing 'resume' field"}), 400
        resume_text = data["resume"]
        matches = [
            {"job_description": j, "score": score_match(j, resume_text)}
            for j in JOBS
        ]
        matches.sort(key=lambda x: x["score"], reverse=True)
        return jsonify({
            "resume": resume_text,
            "matches": matches
        }), 200
    except Exception as e:
        logger.exception(f"Error in score_jobs_for_resume: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5002)