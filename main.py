from pydantic import BaseModel
from datetime import datetime
from textblob import TextBlob
import sqlite3
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Montando a pasta 'static' corretamente
app.mount("/static", StaticFiles(directory="static"), name="static")

# Indicando a pasta onde está o HTML
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---- Banco de dados ----
conn = sqlite3.connect('aura.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    aura INTEGER DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS relatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    texto TEXT,
    valor_aura INTEGER,
    data TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
)
''')
conn.commit()

# ---- Modelos de dados ----
class Relato(BaseModel):
    nome: str
    texto: str

# ---- Funções auxiliares ----
def analisar_sentimento(texto):
    blob = TextBlob(texto)
    polaridade = blob.sentiment.polarity  # -1 a 1

    if polaridade > 0.3:
        return "positivo", int(polaridade * 20)
    elif polaridade < -0.3:
        return "negativo", int(polaridade * 20)
    else:
        return "neutro", 0

def obter_ou_criar_usuario(nome):
    cursor.execute("SELECT id, aura FROM usuarios WHERE nome = ?", (nome,))
    resultado = cursor.fetchone()
    if resultado:
        return resultado[0], resultado[1]
    else:
        cursor.execute("INSERT INTO usuarios (nome, aura) VALUES (?, 0)", (nome,))
        conn.commit()
        return cursor.lastrowid, 0

# ---- Rotas ----
@app.post("/relato")
def processar_relato(relato: Relato):
    usuario_id, aura_atual = obter_ou_criar_usuario(relato.nome)

    sentimento, valor = analisar_sentimento(relato.texto)
    nova_aura = aura_atual + valor

    cursor.execute("UPDATE usuarios SET aura = ? WHERE id = ?", (nova_aura, usuario_id))
    cursor.execute(
        "INSERT INTO relatos (usuario_id, texto, valor_aura, data) VALUES (?, ?, ?, ?)",
        (usuario_id, relato.texto, valor, datetime.now().isoformat())
    )
    conn.commit()

    return {
        "mensagem": f"Sentimento detectado: {sentimento}. Valor de aura: {valor}.",
        "aura_atual": nova_aura
    }

@app.get("/aura/{nome}")
def consultar_aura(nome: str):
    cursor.execute("SELECT aura FROM usuarios WHERE nome = ?", (nome,))
    resultado = cursor.fetchone()
    if resultado:
        return {"nome": nome, "aura": resultado[0]}
    else:
        return {"mensagem": "Usuário não encontrado."}
