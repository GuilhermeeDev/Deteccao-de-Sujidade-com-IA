./scripts/cleanerCache.bash ~/Apps/@Codando/@Projetos/Placas-Solares

python -m uvicorn api_client:app --port 8000 --reload
python -m uvicorn api_inference:app --port 8001 --reload


