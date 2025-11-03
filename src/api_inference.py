import os
import logging
import requests
import base64
import time
from io import BytesIO
from datetime import datetime
from PIL import Image
import torch
import torchvision.transforms as transforms
from fastapi import FastAPI, HTTPException, Query
from config.middleware.cors_middleware import setup_cors
from arqui_models.arq_models import custom_alexnet, custom_resnet50, custom_vgg16, custom_inceptionv3
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from arqui_models.models import criar_tabela_resultados
from config.settings import settings
settings = settings

# --- Conexão com o banco de dados ---
Base = declarative_base()
ResultadoDB = criar_tabela_resultados(Base)

engine = create_engine(settings.DATABASE_URL)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()
setup_cors(app)
logging.basicConfig(level=logging.INFO)

loaded_models = []
num_classes = 2
class_names = ['clean', 'dirty']
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

HEADERS = {
    "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def aguardar_imagem_github(github_api_url, tentativas=3, intervalo=1):

    for _ in range(tentativas):
        resp = requests.get(github_api_url, headers=HEADERS)
        if resp.status_code == 200:
            return resp
        time.sleep(intervalo)

def edita_git(image_url: str, caracteristica: str):
    try:
        # Pegando a hora e data para incrementar no nome
        agora = datetime.now()
        hora_data = f"{agora.strftime('%d%m%Y_%H%M')}"
        
        # Extrai o nome do arquivo da URL
        nome_original = image_url.split("/")[-1]
        extensao = os.path.splitext(nome_original)[-1]
        novo_nome = f"{caracteristica}_{hora_data}{extensao}"
        
        # Constrói a URL da API para o arquivo atual
        github_api_url = f"https://api.github.com/repos/{settings.REPO_OWNER}/{settings.REPO_NAME}/contents/imagens/{nome_original}"

        # Obtém o conteúdo atual do arquivo
        get_response = aguardar_imagem_github(github_api_url)
        if not get_response:
            logging.error(f"Erro ao acessar a imagem no GitHub após várias tentativas.")
            return None

        file_sha = get_response.json()["sha"]
        file_content_encoded = get_response.json()["content"]
        file_content_decoded = base64.b64decode(file_content_encoded)

        # Cria o novo arquivo com o nome atualizado
        upload_url = f"https://api.github.com/repos/{settings.REPO_OWNER}/{settings.REPO_NAME}/contents/imagens/{novo_nome}"
        
        
        # Verifica se o novo nome já existe para pegar o sha
        check_response = requests.get(upload_url, headers=HEADERS)
        if check_response.status_code == 200:
            sha_novo = check_response.json().get("sha")
        else:
            sha_novo = None

        # Monta o payload com ou sem sha
        payload_upload = {
            "message": f"Renomeando imagem para {novo_nome}",
            "content": base64.b64encode(file_content_decoded).decode("utf-8"),
            "branch": settings.BRANCH
        }
        if sha_novo:
            payload_upload["sha"] = sha_novo

        put_response = requests.put(upload_url, headers=HEADERS, json=payload_upload)
        if put_response.status_code not in [200, 201]:
            logging.error(f"Erro ao renomear a imagem: {put_response.text}")
            return None

        # Deleta o arquivo antigo
        delete_payload = {
            "message": f"Removendo imagem antiga {nome_original}",
            "sha": file_sha,
            "branch": settings.BRANCH
        }

        delete_response = requests.delete(github_api_url, headers=HEADERS, json=delete_payload)
        if delete_response.status_code != 200:
            logging.warning(f"Imagem renomeada, mas não foi possível excluir a antiga: {delete_response.text}")

        link_imagem = f"https://raw.githubusercontent.com/{settings.REPO_OWNER}/{settings.REPO_NAME}/{settings.BRANCH}/imagens/{novo_nome}"
        logging.info(f"Imagem renomeada com sucesso: {link_imagem}")
        # Retorna o novo link da imagem
        return link_imagem

    except Exception as e:
        logging.error(f"Erro ao atualizar o nome da imagem: {str(e)}")
        return None
    
def process_image(image_url: str):
    try: 

        if settings.REPOSITORIO == "github":
            logging.info(f"Baixando imagem: {image_url}")
            response = requests.get(image_url)  # Baixando a imagem do repositório do GitHub
            logging.info(f"Status download raw URL: {response.status_code}")

            if response.status_code != 200:
                raise HTTPException(status_code=404,
                detail=f"Imagem não encontrada: status {response.status_code}")
            img = Image.open(BytesIO(response.content))
               
        if settings.REPOSITORIO == "local":
            logging.info(f"Acessando imagem local: {image_url}")
            img = Image.open(image_url)
            
        resul_inferencias, resul_final = [],[]

        # Inferência CNN
        for model_name, model_instance in loaded_models:
            logging.info(f"Rodando inferência com o modelo {model_name}")
            
            # Define o tamanho correto da imagem baseado no modelo
            if "inception" in model_name.lower():
                transform = transforms.Compose([
                    transforms.Resize((299, 299)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                ])
            else:
                transform = transforms.Compose([
                    transforms.Resize((224, 224)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                ])
            
            img_tensor = transform(img).unsqueeze(0).to(device)

            with torch.no_grad():
                output = model_instance(img_tensor)

            # Se for inception com saída auxiliar, pegue apenas a saída principal
            if isinstance(output, tuple):
                output = output[0]

            _, predicted = torch.max(output, 1)
            class_id = predicted.item()
            resul_inferencias.append(["clean" if class_id == 0 else "dirty"])

        logging.info(f"Log da Lista de inferencia: {resul_inferencias}")
        
        cont_clean, cont_dirty = 0, 0

        for pos in resul_inferencias:
            valor = pos[0]
            if valor == "clean":
                cont_clean += 1
            else:
                cont_dirty += 1

        if cont_clean > cont_dirty:
            resul_final.append("limpo")
            caracteristica = 'clean'
        else:
            resul_final.append("sujo")
            caracteristica = 'dirty'
        
        logging.info(f"Limpo: {cont_clean}, Sujo: {cont_dirty}")
        logging.info(f"Resultado final da imagem: {resul_final[0]}")
        
        logging.info("settings.REPOSITORIO: " + settings.REPOSITORIO)
        
        if settings.REPOSITORIO== "github":
            link = edita_git(image_url,caracteristica)
        else:
            link = image_url
            
        return resul_final[0], link
  
    except Exception as e:
        logging.error(f"Erro ao processar a imagem: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao processar a imagem")

def carregar_modelos():
    global loaded_models
    loaded_models.clear()
    model_names = [f for f in os.listdir(settings.PATH_MODELOS) if f.endswith('.pth')]
    models_folder = os.path.join(settings.PATH_MODELOS)

    for model_file_name in model_names:
        model_path = os.path.join(models_folder, model_file_name)

        if "alexnet" in model_file_name:
            model_instance = custom_alexnet(num_classes)
        elif "resnet" in model_file_name:
            model_instance = custom_resnet50(num_classes, in_channels=3)
        elif "vgg" in model_file_name:
            model_instance = custom_vgg16(num_classes)
        elif "inception" in model_file_name:
            model_instance = custom_inceptionv3(num_classes)
        else:
            continue

        try:
            model_instance.load_state_dict(torch.load(model_path, map_location=device), strict=False)
            model_instance.to(device)
            model_instance.eval()
            loaded_models.append((model_file_name, model_instance))
            logging.info(f"Modelo {model_file_name} carregado com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao carregar {model_file_name}: {e}")

def salvar_resultado_no_banco(ResultadoDB, caracteristica, data_proc, hora_proc, link_imagem):
    try:
        db = SessionLocal()
        novo_resultado = ResultadoDB(
            caracteristica=caracteristica,
            data_processamento=data_proc,
            hora_processamento=hora_proc,
            link_imagem=link_imagem
        )
        db.add(novo_resultado)
        db.commit()
        db.refresh(novo_resultado)
        logging.info(f"Resultado salvo no banco: ID {novo_resultado.id}")
        return novo_resultado
    except Exception as e:
        logging.error(f"Erro ao salvar no banco: {str(e)}")
        raise
    finally:
        db.close()

carregar_modelos()

@app.post("/processar_imagem/")
async def processar_imagem(image_url: str = Query(...)):
    try:
        processar = process_image(image_url)
        plate_status = processar[0]
        plate_status = plate_status.replace("root:", "").strip()
        
        if plate_status in ["clean", "limpo"]:
            resultado = "Limpo"
        else:
            resultado = "Sujo"

        data_atual = datetime.now().strftime("%Y-%m-%d")
        hora_atual = datetime.now().strftime("%H:%M:%S")
        link = processar[1]

        # Salva no banco
        resultado_salvo = salvar_resultado_no_banco(
            ResultadoDB, resultado, data_atual, hora_atual, link
        )

        # Retorna resposta
        return {
            "id": resultado_salvo.id,
            "caracteristica": resultado_salvo.caracteristica,
            "data_processamento": resultado_salvo.data_processamento,
            "hora_processamento": resultado_salvo.hora_processamento,
            "link_imagem": resultado_salvo.link_imagem,
        }

    except Exception as e:
        logging.error(f"Erro ao processar a imagem: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao processar a imagem.")

@app.get("/resultados/")
def listar_resultados():
    try:
        db = SessionLocal()
        resultados = db.query(ResultadoDB).order_by(ResultadoDB.id).all()
        return [
            {
                "id": r.id,
                "caracteristica": r.caracteristica,
                "data_processamento": r.data_processamento,
                "hora_processamento": r.hora_processamento,
                "link_imagem": r.link_imagem,
            }
            for r in resultados
        ]
    except Exception as e:
        logging.error(f"Erro ao buscar resultados: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar resultados.")
    finally:
        db.close()    
