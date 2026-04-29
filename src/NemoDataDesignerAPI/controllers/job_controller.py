import time, uuid, os
import pandas as pd
from pathlib import Path
from typing import Optional
from config import JOB_STORE, OUTPUT_DIR, UPLOAD_DIR, COLUMN_CACHE, DATASTORE_ENDPOINT, NEMO_MICROSERVICES_BASE_URL, FIXED_MODEL_ALIAS
from models.requests import GenerateRequest
from utils.encryption import encrypt_auth_data
from nemo_microservices.data_designer.essentials import DataDesignerConfigBuilder, InferenceParameters, ModelConfig, NeMoDataDesignerClient
import db

client = NeMoDataDesignerClient(base_url=NEMO_MICROSERVICES_BASE_URL)

def prepare_tunnel(req):
    encrypted_token = encrypt_auth_data({"key": req.provider_api_key, "url": req.provider_base_url, "version": req.provider_api_version})
    return f"{req.model_id}__{req.model_provider}__{encrypted_token}"

def process_seed_and_cache(file_path):
    try:
        df = pd.read_csv(file_path, nrows=0)
        repo_id = f"data-designer/{file_path.stem}"
        COLUMN_CACHE[repo_id] = df.columns.tolist()
        return client.upload_seed_dataset(dataset=file_path, repo_id=repo_id, datastore_settings={"endpoint": DATASTORE_ENDPOINT})
    except Exception as e:
        print(f"❌ Seed Error: {e}"); raise e

def build_config(req, tunnel_name, seed_ref=None):
    model_configs = [ModelConfig(alias=FIXED_MODEL_ALIAS, model=tunnel_name, provider="stateless_proxy",
        inference_parameters=InferenceParameters(temperature=req.temperature, top_p=req.top_p, max_tokens=req.max_tokens))]
    builder = DataDesignerConfigBuilder(model_configs=model_configs)
    if seed_ref: builder.with_seed_dataset(seed_ref)
    if req.sampler_columns:
        for c in req.sampler_columns: builder.add_column(column_type="sampler", **c.model_dump(exclude_none=True))
    if req.expression_columns:
        for c in req.expression_columns: builder.add_column(column_type="expression", **c.model_dump(exclude_none=True))
    if req.llm_text_columns:
        for c in req.llm_text_columns: builder.add_column(column_type="llm-text", model_alias=FIXED_MODEL_ALIAS, **c.model_dump(exclude_none=True))
    if req.llm_code_columns:
        for c in req.llm_code_columns: builder.add_column(column_type="llm-code", model_alias=FIXED_MODEL_ALIAS, **c.model_dump(exclude_none=True))
    if req.llm_structured_columns:
        for c in req.llm_structured_columns: builder.add_column(column_type="llm-structured", model_alias=FIXED_MODEL_ALIAS, **c.model_dump(exclude_none=True))
    if req.llm_judge_columns:
        for c in req.llm_judge_columns:
            builder.add_column(name=c.name, column_type="llm-judge", model_alias=FIXED_MODEL_ALIAS,
                prompt=c.prompt, scores=[s.model_dump() for s in c.scores], system_prompt=c.system_prompt)
    if req.validation_columns:
        for c in req.validation_columns: builder.add_column(column_type="validation", **c.model_dump(exclude_none=True))
    builder.validate()
    return builder

def run_job(job_id: str, req: GenerateRequest, seed_path: Optional[Path], mode: str = "create"):
    try:
        tunnel = prepare_tunnel(req)
        seed_ref = process_seed_and_cache(seed_path) if seed_path else None
        config = build_config(req, tunnel, seed_ref)
        start = time.time()
        job = client.create(config, num_records=req.num_records)
        job.wait_until_done()
        duration = time.time() - start
        df = job.load_dataset()
        records = df.to_dict(orient="records")

        if mode == "create":
            csv_filename = f"generated_{job_id}.csv"
            df.to_csv(OUTPUT_DIR / csv_filename, index=False)
        else:
            csv_filename = ""

        result = {"num_records": len(records), "duration_seconds": round(duration, 2), "dataset": records}
        JOB_STORE[job_id].update({"status": "completed", "result": result})
        db.update_completed(job_id, result, csv_filename)

    except Exception as e:
        JOB_STORE[job_id].update({"status": "failed", "error": str(e)})
        db.update_failed(job_id, str(e))
    finally:
        if seed_path and seed_path.exists(): os.remove(seed_path)
