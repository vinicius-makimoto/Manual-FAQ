"""Autenticação OAuth e integrações formatadas com Google Sheets e Docs."""

import os
import re
from datetime import datetime
from pathlib import Path

from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
]
BASE_DIR = Path(__file__).parent


def autenticar_google():
    token_path = BASE_DIR / "token.json"
    credentials_path = BASE_DIR / "credentials.json"
    # Load the scopes actually stored in the token; passing SCOPES here would
    # override the saved scope list and could falsely make an old Sheets-only
    # token look authorized for Docs.
    credenciais = Credentials.from_authorized_user_file(str(token_path)) if token_path.exists() else None
    if credenciais and not credenciais.has_scopes(SCOPES):
        token_path.unlink(missing_ok=True)
        credenciais = None
    if credenciais and credenciais.expired and credenciais.refresh_token:
        credenciais.refresh(Request())
    if not credenciais or not credenciais.valid:
        if not credentials_path.exists():
            raise FileNotFoundError("Coloque credentials.json (OAuth Desktop) na pasta do projeto.")
        fluxo = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        credenciais = fluxo.run_local_server(port=0)
    token_path.write_text(credenciais.to_json(), encoding="utf-8")
    return credenciais


def _texto_sem_markdown(texto: str) -> str:
    """Converte Markdown simples em texto legível para células e documentos Google."""
    linhas = []
    for linha in texto.replace("\r\n", "\n").split("\n"):
        linha = re.sub(r"^\s*#{1,6}\s+", "", linha)
        linha = re.sub(r"^\s*[-*+]\s+", "• ", linha)
        linha = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", linha)
        linha = linha.replace("**", "").replace("__", "")
        linha = linha.replace("`", "")
        if linha.strip().startswith("```"):
            continue
        linhas.append(linha.rstrip())
    return "\n".join(linhas).strip()


def _formatar_planilha(servico, planilha_id: str, sheet_id: int, linha: int):
    servico.spreadsheets().batchUpdate(
        spreadsheetId=planilha_id,
        body={"requests": [
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.10, "green": 0.28, "blue": 0.42}, "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP", "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}}, "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,wrapStrategy,textFormat)"}},
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": linha + 1, "startColumnIndex": 0, "endColumnIndex": 10}, "cell": {"userEnteredFormat": {"verticalAlignment": "TOP", "wrapStrategy": "WRAP"}}, "fields": "userEnteredFormat(verticalAlignment,wrapStrategy)"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 170}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2}, "properties": {"pixelSize": 320}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3}, "properties": {"pixelSize": 620}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 3, "endIndex": 4}, "properties": {"pixelSize": 210}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 5}, "properties": {"pixelSize": 110}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 7}, "properties": {"pixelSize": 140}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 7, "endIndex": 8}, "properties": {"pixelSize": 170}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 8, "endIndex": 9}, "properties": {"pixelSize": 210}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 9, "endIndex": 10}, "properties": {"pixelSize": 260}, "fields": "pixelSize"}},
            {"autoResizeDimensions": {"dimensions": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": linha, "endIndex": linha + 1}}},
        ]},
    ).execute()


def registrar_chamado(
    planilha_id: str,
    pergunta: str,
    resposta: str,
    categoria: str,
    prioridade: str,
    solicitante: str,
    email: str,
) -> dict:
    credenciais = autenticar_google()
    servico = build("sheets", "v4", credentials=credenciais)
    meta = servico.spreadsheets().get(spreadsheetId=planilha_id, fields="sheets(properties(sheetId,title))").execute()
    abas = meta.get("sheets", [])
    if not abas:
        raise ValueError("A planilha não contém abas.")
    primeira_aba = abas[0]["properties"]
    sheet_id = primeira_aba["sheetId"]
    aba = primeira_aba["title"].replace("'", "''")
    cabecalhos = ["Data/Hora", "Pergunta", "Resposta", "Categoria", "Prioridade", "Status", "Útil?", "ID do chamado", "Solicitante", "E-mail"]
    servico.spreadsheets().values().update(
        spreadsheetId=planilha_id,
        range=f"'{aba}'!A1:J1",
        valueInputOption="RAW",
        body={"values": [cabecalhos]},
    ).execute()
    agora = datetime.now().astimezone()
    ticket_id = f"FAQ-{agora:%y%m%d-%H%M%S}"
    resultado = servico.spreadsheets().values().append(
        spreadsheetId=planilha_id,
        range=f"'{aba}'!A:J",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [[agora.strftime("%d/%m/%Y %H:%M:%S"), _texto_sem_markdown(pergunta), _texto_sem_markdown(resposta), categoria, prioridade, "Aberto", "Não", ticket_id, solicitante, email]]},
    ).execute()
    match = re.search(r"!A(\d+):J", resultado.get("updates", {}).get("updatedRange", ""))
    if match:
        _formatar_planilha(servico, planilha_id, sheet_id, int(match.group(1)) - 1)
    return {"id": ticket_id, "linha": int(match.group(1)) if match else None, "categoria": categoria, "prioridade": prioridade, "status": "Aberto"}


def listar_chamados(planilha_id: str) -> list[dict]:
    """Lê chamados classificados da primeira aba da planilha."""
    servico = build("sheets", "v4", credentials=autenticar_google())
    meta = servico.spreadsheets().get(spreadsheetId=planilha_id, fields="sheets(properties(title))").execute()
    abas = meta.get("sheets", [])
    if not abas:
        return []
    aba = abas[0]["properties"]["title"].replace("'", "''")
    linhas = servico.spreadsheets().values().get(spreadsheetId=planilha_id, range=f"'{aba}'!A1:J").execute().get("values", [])
    chamados = []
    for numero_linha, linha in enumerate(linhas[1:], start=2):
        valores = linha + [""] * (10 - len(linha))
        if not str(valores[5]).strip():
            continue
        chamados.append({
            "Data/Hora": valores[0], "Pergunta": valores[1], "Resposta": valores[2],
            "Categoria": valores[3], "Prioridade": valores[4], "Status": valores[5],
            "Útil?": valores[6], "ID": valores[7],
            "Solicitante": valores[8], "E-mail": valores[9], "_linha": numero_linha,
        })
    return chamados


def atualizar_status_chamado(planilha_id: str, numero_linha: int, status: str) -> None:
    servico = build("sheets", "v4", credentials=autenticar_google())
    meta = servico.spreadsheets().get(spreadsheetId=planilha_id, fields="sheets(properties(title))").execute()
    aba = meta["sheets"][0]["properties"]["title"].replace("'", "''")
    servico.spreadsheets().values().update(
        spreadsheetId=planilha_id,
        range=f"'{aba}'!F{numero_linha}",
        valueInputOption="RAW",
        body={"values": [[status]]},
    ).execute()


def registrar_consulta_docs(documento_id: str, pergunta: str, resposta: str) -> str:
    """Acrescenta uma consulta em um Google Doc existente, com títulos formatados."""
    servico = build("docs", "v1", credentials=autenticar_google())
    documento = servico.documents().get(documentId=documento_id).execute()
    fim = documento.get("body", {}).get("content", [])[-1]["endIndex"] - 1
    agora = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M")
    titulo = f"Consulta de suporte - {agora}\n"
    rotulo_pergunta = "Pergunta\n"
    rotulo_resposta = "Resposta\n"
    conteudo_pergunta = _texto_sem_markdown(pergunta) + "\n\n"
    conteudo_resposta = _texto_sem_markdown(resposta) + "\n\n"
    texto = titulo + rotulo_pergunta + conteudo_pergunta + rotulo_resposta + conteudo_resposta
    servico.documents().batchUpdate(documentId=documento_id, body={"requests": [
        {"insertText": {"location": {"index": fim}, "text": texto}},
        {"updateParagraphStyle": {"range": {"startIndex": fim, "endIndex": fim + len(titulo)}, "paragraphStyle": {"namedStyleType": "HEADING_1"}, "fields": "namedStyleType"}},
        {"updateParagraphStyle": {"range": {"startIndex": fim + len(titulo), "endIndex": fim + len(titulo) + len(rotulo_pergunta)}, "paragraphStyle": {"namedStyleType": "HEADING_2"}, "fields": "namedStyleType"}},
        {"updateParagraphStyle": {"range": {"startIndex": fim + len(titulo) + len(rotulo_pergunta) + len(conteudo_pergunta), "endIndex": fim + len(titulo) + len(rotulo_pergunta) + len(conteudo_pergunta) + len(rotulo_resposta)}, "paragraphStyle": {"namedStyleType": "HEADING_2"}, "fields": "namedStyleType"}},
    ]}).execute()
    return f"https://docs.google.com/document/d/{documento_id}/edit"
