import pandas as pd
import re
import os
from sklearn.metrics.pairwise import cosine_similarity
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL")       
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL")      

rag_df = pd.read_csv("data/RAG.csv")
rag_df['Level 1 Term'] = rag_df['Level 1 Term'].fillna(method='ffill')
rag_df['Level 2 Term'] = rag_df['Level 2'].fillna(rag_df['Level 1 Term'])

EXCLUDE_TERMS = [
    "No Apparent Adverse Event",
    "Insufficient Information",
    "Appropriate Term/Code Not Available"
]

def strip_problem_prefix(definition):
    return re.sub(r'^Problem associated with\s+', '', definition, flags=re.IGNORECASE)

def retrieve_topk_rag(event_desc, top_k=5):
    level1_meta = (
        rag_df.dropna(subset=['Level 1 Term'])
        .drop_duplicates(subset=['Level 1 Term'])[['Level 1 Term', 'Definition', 'FDA Code']]
        .reset_index(drop=True)
    )
    level1_meta = level1_meta[~level1_meta['Level 1 Term'].isin(EXCLUDE_TERMS)]
    level1_meta['search_text'] = level1_meta['Level 1 Term'] + ": " + level1_meta['Definition']

    event_emb = client.embeddings.create(input=[event_desc], model=EMBED_MODEL).data[0].embedding
    def_embs = client.embeddings.create(input=level1_meta['search_text'].tolist(), model=EMBED_MODEL).data
    def_embs = [e.embedding for e in def_embs]

    sims = cosine_similarity([event_emb], def_embs)[0]
    level1_meta['similarity'] = sims
    return level1_meta.sort_values('similarity', ascending=False).head(top_k)

def retrieve_topk_level2_rag(event_desc, level1_terms, top_k=5):
    candidates = []
    for lvl1 in level1_terms:
        level2_meta = (
            rag_df[rag_df['Level 1 Term'] == lvl1]
            .dropna(subset=['Level 2 Term'])
            .drop_duplicates(subset=['Level 2 Term'])[['Level 2 Term', 'Definition', 'FDA Code']]
            .reset_index(drop=True)
        )
        if level2_meta.empty:
            continue

        event_emb = client.embeddings.create(input=[event_desc], model=EMBED_MODEL).data[0].embedding
        def_embs = client.embeddings.create(input=level2_meta['Definition'].tolist(), model=EMBED_MODEL).data
        def_embs = [e.embedding for e in def_embs]

        sims = cosine_similarity([event_emb], def_embs)[0]
        level2_meta['similarity'] = sims
        level2_meta['Level 1 Term'] = lvl1
        candidates.append(level2_meta.sort_values('similarity', ascending=False).head(top_k))
    return pd.concat(candidates, ignore_index=True) if candidates else pd.DataFrame()

def predict_fda_code(event_desc: str, prod_id: str) -> dict:
    try:
        level1_topk = retrieve_topk_rag(event_desc, top_k=5)
        level1_terms = level1_topk['Level 1 Term'].tolist()

        level2_topk = retrieve_topk_level2_rag(event_desc, level1_terms, top_k=5)
        if level2_topk.empty:
            return {"code": "N/A", "error": "No suitable Level 2 terms found."}

        context = "\n".join([
            f"- {row['FDA Code']}: {row['Level 2 Term']} — {strip_problem_prefix(row['Definition'])}"
            for _, row in level2_topk.iterrows()
        ])

        prompt = (
            f"Given the following event description:\n"
            f"Event Description: {event_desc}\n"
            f"Product Identification: {prod_id}\n\n"
            f"Choose ONLY ONE FDA code from the following candidates which most appropriately describes the problem:\n{context}\n\n"
            f"Return ONLY the SINGLE FDA Code (e.g., 1234)."
        )

        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert at classifying medical device problem codes."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=20,
            temperature=0
        )
        raw_output = response.choices[0].message.content.strip()
        code_match = re.search(r"\b\d{3,5}\b", raw_output)

        if code_match:
            matched_code = code_match.group()
            matched_row = rag_df[rag_df['FDA Code'] == int(matched_code)]

            if not matched_row.empty:
                level1_term = matched_row['Level 1 Term'].iloc[0]
                level2_term = matched_row['Level 2 Term'].iloc[0]
                matched_term = level2_term if level2_term != level1_term else level1_term
            else:
                matched_term = "Unknown"

            return {
                "code": matched_code,
                "term": matched_term,
                "raw_output": raw_output
            }
        else:
            return {
                "code": "N/A",
                "term": "Unknown",
                "raw_output": raw_output
            }
        
    except Exception as e:
        return {"code": "N/A", "error": str(e)}
