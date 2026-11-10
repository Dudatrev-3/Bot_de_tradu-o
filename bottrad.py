import os
import requests
from requests.auth import AuthBase
from dotenv import load_dotenv

load_dotenv(".env")
DEEPL_KEY = os.getenv("DEEPL_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPL_URL = "https://api-free.deepl.com/v2/translate"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

IDIOMA_PADRAO = "PT-BR"

IDIOMAS = {
    "EN-US", "ES", "FR", "JA", "PT-BR", "RU",
}

APELIDOS = {"EN": "EN-US", "PT": "PT-BR"}

AJUDA = (
    "Envie: IDIOMA: texto\n"
    "Exemplos: \n"
    "EN: olá, tudo bem?\n"
    "JA: Obrigado\n"
    f"sem idioma, traduzo para {IDIOMA_PADRAO}.\n"
    "Idiomas possíveis: Inglês, Espanhol, Francês, Japonês, Português, Russo.\n\n"
)

class DeepLAuth(AuthBase):
    def __init__(self, key):
        self.key = key
    def __call__(self, r):
        r.headers["Authorization"] = f"DeepL-Auth-Key {self.key}"
        return r
deepl_session = requests.Session()
deepl_session.auth = DeepLAuth(DEEPL_KEY)

tg = requests.Session()

def separar_idioma(mensagem):
    if ":" in mensagem:
        prefixo, resto = mensagem.split(":", 1)
        codigo = prefixo.strip().upper()
        codigo = APELIDOS.get(codigo, codigo)
        if codigo in IDIOMAS and resto.strip():
            return codigo, resto.strip()
    return IDIOMA_PADRAO, mensagem.strip()


def traduzir(texto, idioma):
    resposta = deepl_session.post(
        DEEPL_URL,
        json = {"text": [texto], "target_lang": idioma},
        auth = DeepLAuth(DEEPL_KEY),
        timeout = 15,
    )
    resposta.raise_for_status()
    t = resposta.json()["translations"][0]
    return t ["text"], t["detected_source_language"]


#Recebe
def receber(offset = None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    resposta = tg.get(f"{TELEGRAM_URL}/getUpdates", params = params, timeout = 40)
    return resposta.json()["result"]

#Envia
def enviar(chat_id, texto):
    tg.post(
        f"{TELEGRAM_URL}/sendMessage",
        data={"chat_id": chat_id, "text": texto},
        timeout = 15
    )

def main():
    offset = None
    while True:
        for update in receber(offset):
            offset = update["update_id"] + 1

            msg = update.get("message")
            if not msg or "text" not in msg:
                continue

            chat_id = msg["chat"]["id"]
            texto = msg["text"]

            if texto.startswith("/start") or texto.startswith("/ajuda"):
                enviar(chat_id, AJUDA)
                continue

            idioma, conteudo = separar_idioma(texto)
            try:
                traducao, origem = traduzir(conteudo, idioma)
                enviar(chat_id, f"[{origem} -> {idioma}]\n{traducao}")
            except requests.RequestException as e:
                enviar(chat_id, f"Erro na tradução: {e}")
if __name__ == "__main__":
    main()