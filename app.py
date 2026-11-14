"""Interface Streamlit do Manual de FAQ e painel de chamados."""

import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from agent import MODELO_GROQ, abrir_chamado, responder_faq
from google_tools import atualizar_status_chamado, listar_chamados

load_dotenv()
st.set_page_config(page_title="Manual de FAQ | Suporte TI", page_icon="🛠️", layout="wide")
css_path = Path(__file__).with_name("styles.css")
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")


@st.dialog("Resposta do Manual de FAQ", width="large")
def mostrar_resposta_modal():
    registro = st.session_state.get("resposta_pendente")
    if not registro:
        return
    st.markdown(registro["texto"])
    if registro.get("fontes"):
        st.markdown("**Fontes consultadas**")
        for fonte in registro["fontes"]:
            st.markdown(f"- [{fonte['titulo']}]({fonte['url']})")
    if registro.get("documento_url"):
        st.link_button("Abrir registro no Google Docs", registro["documento_url"])
    for aviso in registro.get("avisos_busca", []):
        st.caption(aviso)
    for aviso in registro.get("avisos_registro", []):
        st.caption(aviso)

    st.divider()
    st.markdown("**Esta resposta foi útil?**")
    sim, nao = st.columns(2)
    with sim:
        if st.button("Sim, resolveu minha dúvida", type="primary", use_container_width=True, key="feedback_sim"):
            st.session_state.resposta_pendente = None
            st.session_state.coletar_dados_solicitante = False
            st.session_state.aviso_feedback = "Obrigado pelo feedback! Nenhum chamado foi aberto."
            st.rerun()
    with nao:
        if st.button("Não, abrir chamado para o suporte", use_container_width=True, key="feedback_nao"):
            if not SHEETS_ID:
                st.error("Configure GOOGLE_SHEETS_ID para abrir um chamado.")
            else:
                st.session_state.coletar_dados_solicitante = True
                st.rerun()


@st.dialog("Identificação para atendimento", width="small")
def mostrar_identificacao_modal():
    registro = st.session_state.get("resposta_pendente")
    if not registro:
        st.session_state.coletar_dados_solicitante = False
        return
    st.caption("Informe seus dados para que a equipe saiba quem abriu a solicitação e possa retornar.")
    with st.form("identificacao_chamado"):
        nome = st.text_input("Nome completo", max_chars=120)
        email = st.text_input("E-mail para contato", max_chars=254)
        enviar_chamado = st.form_submit_button(
            "Confirmar e abrir chamado",
            type="primary",
            use_container_width=True,
        )
    voltar = st.button("Voltar à resposta", key="voltar_resposta")
    if voltar:
        st.session_state.coletar_dados_solicitante = False
        st.rerun()
    if enviar_chamado:
        nome = nome.strip()
        email = email.strip()
        if not nome:
            st.error("Informe seu nome completo.")
        elif not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            st.error("Informe um endereço de e-mail válido.")
        else:
            try:
                with st.spinner("Classificando e registrando o chamado..."):
                    chamado = abrir_chamado(registro["pergunta"], registro["texto"], nome, email)
                st.session_state.resposta_pendente = None
                st.session_state.coletar_dados_solicitante = False
                st.session_state.aviso_feedback = (
                    f"Chamado {chamado['id']} registrado para {nome} ({email}), como "
                    f"{chamado['categoria']} (prioridade {chamado['prioridade']})."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Não foi possível registrar o chamado: {exc}")


with st.sidebar:
    st.markdown("<div class='brand-mark'>IT SUPPORT</div>", unsafe_allow_html=True)
    st.title("Manual de FAQ")
    st.caption("Central de suporte de TI")
    st.divider()
    for label, configured in (
        ("IA Groq / GPT-OSS", bool(os.getenv("GROQ_API_KEY"))),
        ("Google Sheets", bool(SHEETS_ID and "gcp_service_account" in st.secrets)),
        ("Google Docs", bool(os.getenv("GOOGLE_DOCS_ID") and "gcp_service_account" in st.secrets)),
    ):
        st.write(("🟢 " if configured else "⚪ ") + label)
    st.caption("Modelo de IA")
    st.markdown(f"<div class='model-pill'>{MODELO_GROQ}</div>", unsafe_allow_html=True)

st.markdown("<div class='eyebrow'>CENTRAL DE AJUDA</div>", unsafe_allow_html=True)
st.title("Suporte de TI")
st.markdown("Encontre orientações no FAQ ou acompanhe os chamados encaminhados à equipe.")
aba_faq, aba_dashboard = st.tabs(["Perguntar ao FAQ", "Dashboard de chamados"])

with aba_faq:
    if aviso := st.session_state.pop("aviso_feedback", None):
        st.success(aviso)
    with st.container(border=True):
        st.subheader("Descreva sua dúvida")
        with st.form("pergunta_faq", clear_on_submit=True):
            pergunta = st.text_area(
                "Qual problema você está enfrentando?",
                height=110,
                placeholder="Ex.: Meu computador não conecta à rede Wi-Fi. O que devo verificar?",
                label_visibility="collapsed",
            )
            enviar = st.form_submit_button("Consultar FAQ", type="primary")
    if enviar:
        if not pergunta.strip():
            st.warning("Digite uma pergunta para continuar.")
        else:
            with st.spinner("Consultando o manual..."):
                resposta = responder_faq(pergunta.strip())
            if resposta.get("erro"):
                st.error(resposta["erro"])
            else:
                resposta["pergunta"] = pergunta.strip()
                st.session_state.resposta_pendente = resposta
                st.rerun()

with aba_dashboard:
    st.subheader("Visão geral dos chamados")
    if not SHEETS_ID:
        st.info("Configure GOOGLE_SHEETS_ID no arquivo .env para carregar os chamados.")
    else:
        atualizar, _ = st.columns([1, 5])
        with atualizar:
            if st.button("Atualizar dados", use_container_width=True):
                st.rerun()
        try:
            todos = listar_chamados(SHEETS_ID)
        except Exception as exc:
            todos = []
            st.error(f"Não foi possível carregar os chamados: {exc}")

        abertos = sum(chamado["Status"] == "Aberto" for chamado in todos)
        andamento = sum(chamado["Status"] == "Em andamento" for chamado in todos)
        concluidos = sum(chamado["Status"] == "Concluído" for chamado in todos)
        alta = sum(chamado["Prioridade"] == "Alta" and chamado["Status"] != "Concluído" for chamado in todos)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total de chamados", len(todos))
        m2.metric("Abertos", abertos)
        m3.metric("Em andamento", andamento)
        m4.metric("Alta prioridade", alta)

        if todos:
            resumo_categoria = pd.Series([c["Categoria"] or "Sem categoria" for c in todos]).value_counts().rename_axis("Categoria").to_frame("Chamados")
            st.markdown("#### Chamados por categoria")
            st.bar_chart(resumo_categoria)

            f1, f2, f3 = st.columns([1, 1, 2])
            opcoes_status = ["Todos", "Aberto", "Em andamento", "Concluído"]
            filtro_status = f1.selectbox("Status", opcoes_status)
            categorias = sorted({c["Categoria"] or "Sem categoria" for c in todos})
            filtro_categoria = f2.selectbox("Categoria", ["Todas"] + categorias)
            busca = f3.text_input("Buscar chamado", placeholder="ID ou palavras da solicitação")

            filtrados = todos
            if filtro_status != "Todos":
                filtrados = [c for c in filtrados if c["Status"] == filtro_status]
            if filtro_categoria != "Todas":
                filtrados = [c for c in filtrados if (c["Categoria"] or "Sem categoria") == filtro_categoria]
            if busca.strip():
                termo = busca.strip().casefold()
                filtrados = [c for c in filtrados if termo in f"{c['ID']} {c['Pergunta']} {c['Categoria']} {c['Solicitante']} {c['E-mail']}".casefold()]

            st.markdown(f"#### Chamados ({len(filtrados)})")
            for chamado in reversed(filtrados):
                with st.container(border=True):
                    meta1, meta2, meta3, meta4 = st.columns([1.3, 2, 1, 1.2])
                    meta1.markdown(f"**{chamado['ID'] or 'Chamado'}**")
                    meta2.markdown(f"**{chamado['Categoria'] or 'Sem categoria'}**")
                    meta3.markdown(f"Prioridade: **{chamado['Prioridade'] or 'Média'}**")
                    meta4.markdown(f"Status: **{chamado['Status']}**")
                    st.caption(f"Aberto em {chamado['Data/Hora']}")
                    st.markdown("**Solicitação**")
                    st.write(chamado["Pergunta"] or "Sem descrição.")
                    st.markdown(f"**Solicitante:** {chamado['Solicitante'] or 'Não informado'} · {chamado['E-mail'] or 'Sem e-mail'}")
                    st.markdown("**Orientação exibida pelo FAQ**")
                    st.markdown(chamado["Resposta"] or "Nenhuma resposta registrada.")
                    with st.form(f"status_chamado_{chamado['_linha']}"):
                        novo_status = st.selectbox(
                            "Atualizar status",
                            ["Aberto", "Em andamento", "Concluído"],
                            index=["Aberto", "Em andamento", "Concluído"].index(chamado["Status"])
                            if chamado["Status"] in ["Aberto", "Em andamento", "Concluído"] else 0,
                            key=f"status_select_{chamado['_linha']}",
                        )
                        salvar_status = st.form_submit_button("Salvar status", type="primary")
                    if salvar_status:
                        try:
                            atualizar_status_chamado(SHEETS_ID, chamado["_linha"], novo_status)
                            st.success("Status atualizado.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Não foi possível atualizar o status: {exc}")
        else:
            st.info("Ainda não há chamados abertos. Eles aparecerão aqui quando alguém avaliar uma resposta como não útil.")

if st.session_state.get("resposta_pendente"):
    if st.session_state.get("coletar_dados_solicitante"):
        mostrar_identificacao_modal()
    else:
        mostrar_resposta_modal()
