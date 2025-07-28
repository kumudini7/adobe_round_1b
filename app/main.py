import os
import json
import time
import pdfplumber
from sentence_transformers import SentenceTransformer, util

INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"
MODEL_PATH = "all-MiniLM-L6-v2"  # ~80MB

def extract_sections(pdf_path):
    sections = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                lines = text.split("\n")
                for line in lines:
                    clean = line.strip()
                    if len(clean.split()) < 3 or len(clean) > 200:
                        continue
                    sections.append({
                        "document": os.path.basename(pdf_path),
                        "page_number": i + 1,
                        "section_title": clean,
                        "text": text
                    })
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
    return sections

def rank_sections(sections, query, model):
    section_texts = [s["text"] for s in sections]
    query_embedding = model.encode(query, convert_to_tensor=True)
    section_embeddings = model.encode(section_texts, convert_to_tensor=True)

    similarities = util.cos_sim(query_embedding, section_embeddings)[0]
    ranked = sorted(zip(sections, similarities), key=lambda x: -x[1])
    
    for rank, (section, score) in enumerate(ranked[:5]):
        section["importance_rank"] = rank + 1
        section["similarity_score"] = float(score)
    return [s for s, _ in ranked[:5]]

def refine_subsections(section, query, model):
    chunks = section["text"].split("\n\n")
    query_embedding = model.encode(query, convert_to_tensor=True)
    sub_embeddings = model.encode(chunks, convert_to_tensor=True)
    sims = util.cos_sim(query_embedding, sub_embeddings)[0]

    results = []
    for i, chunk in enumerate(chunks):
        results.append({
            "document": section["document"],
            "refined_text": chunk.strip(),
            "page_number": section["page_number"],
            "rank": float(sims[i])
        })
    results = sorted(results, key=lambda x: -x["rank"])
    return results[:5]

def main():
    start = time.time()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(os.path.join(INPUT_DIR, "challenge.json"), "r") as f:
        input_data = json.load(f)

    persona = input_data["persona"]["role"]
    job = input_data["job_to_be_done"]["task"]
    documents = input_data["documents"]
    query = f"{persona}. Task: {job}"

    model = SentenceTransformer(MODEL_PATH)

    all_sections = []
    for doc in documents:
        pdf_path = os.path.join(INPUT_DIR, doc["filename"])
        all_sections += extract_sections(pdf_path)

    top_sections = rank_sections(all_sections, query, model)

    refined_subs = []
    for section in top_sections:
        refined_subs += refine_subsections(section, query, model)

    output_json = {
        "metadata": {
            "input_documents": [doc["filename"] for doc in documents],
            "persona": persona,
            "job_to_be_done": job,
            "processing_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        },
        "extracted_sections": [
            {
                "document": sec["document"],
                "section_title": sec["section_title"],
                "importance_rank": sec["importance_rank"],
                "page_number": sec["page_number"]
            }
            for sec in top_sections
        ],
        "subsection_analysis": [
            {
                "document": sub["document"],
                "refined_text": sub["refined_text"],
                "page_number": sub["page_number"]
            }
            for sub in refined_subs
        ]
    }

    with open(os.path.join(OUTPUT_DIR, "output.json"), "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)

    print(f"Done in {time.time() - start:.2f}s")

if __name__ == "__main__":
    main()
