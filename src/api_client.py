from fastapi import FastAPI
from fastapi import HTTPException
import logging
import os
import requests
import base64
import time
from config.middleware.cors_middleware import setup_cors
from fastapi import UploadFile, File
from config.settings import settings

logging.basicConfig(level=logging.INFO)

app = FastAPI()
setup_cors(app)


HEADERS = {
    "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def esperar_disponibilidade_imagem(url, tentativas=3, intervalo=3):
    for _ in range(tentativas):
        response = requests.get(url)
        if response.status_code == 200:
            return True
        time.sleep(intervalo)
    return False

@app.post("/enviar_imagem/")
async def upload_image(files: list[UploadFile] = File(...)):
    resultados = []

    try:
        for file in files: 
            
            if settings.REPOSITORIO == "local":
                file_location = os.path.join(settings.PATH_LOCAL, file.filename)
                with open(file_location, "wb") as f:
                    content = await file.read()
                    f.write(content)
                url_imagem = f"{file_location}"
                logging.info(f"Imagem salva localmente em: {url_imagem}")
               
            if settings.REPOSITORIO == "github":
                image_data = await file.read()
                image_b64 = base64.b64encode(image_data).decode("utf-8")
                github_file_path = f"{settings.UPLOAD_PATH}/{file.filename}"
                github_api_url = f"https://api.github.com/repos/{settings.REPO_OWNER}/{settings.REPO_NAME}/contents/{github_file_path}"
                url_imagem_github = f"https://raw.githubusercontent.com/{settings.REPO_OWNER}/{settings.REPO_NAME}/{settings.BRANCH}/{github_file_path}"

                # Verifica se o arquivo já existe no GitHub
                response = requests.get(github_api_url, headers=HEADERS)
                sha = response.json().get("sha") if response.status_code == 200 else "Arquivo ja existente."

                payload = {
                    "message": f"Upload de {file.filename}",
                    "content": image_b64,
                    "branch": settings.BRANCH
                }
                
                if sha: payload["sha"] = sha

                response = requests.put(github_api_url, json=payload, headers=HEADERS)
                
                if response.status_code not in [200, 201]: raise HTTPException(status_code=400, detail=f"Erro ao enviar {file.filename} para o GitHub")

                # Verifica se a imagem já está disponível no GitHub
                if not esperar_disponibilidade_imagem(url_imagem_github):
                    resultados.append({
                        "arquivo": file.filename,
                        "erro": "Imagem não disponível no GitHub após múltiplas tentativas."
                    })
                    continue
                
            # Enviando para a API-Inferencia
            try:
                if settings.REPOSITORIO == "github":
                    response = requests.post(f"{settings.URL_API_PROCESSAMENTO}?image_url={url_imagem_github}")

                if settings.REPOSITORIO == "local":
                    response = requests.post(f"{settings.URL_API_PROCESSAMENTO}?image_url={url_imagem}")
                
                else:
                    resultados.append({
                        "arquivo": file.filename,
                        "erro": "Repositório inválido."
                    })
                    continue
                
                if response.status_code == 200:
                    resultado = response.json()
                    resultados.append({
                        "arquivo": file.filename,
                        "resultado_inferencia": resultado
                    })
                    
                else:
                    resultados.append({
                        "arquivo": file.filename,
                        "erro": response.text
                    })
                
            except Exception as e:
                resultados.append({
                    "arquivo": file.filename,
                    "erro": str(e)
                })

        return {"Resultados": resultados}

    except Exception as e:
        logging.error(f"Erro interno: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor.")