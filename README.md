# Manual de FAQ - Suporte de TI

Assistente Streamlit para dúvidas de hardware e software, seguindo a arquitetura do projeto Agente People: interface (`main.py`), agente (`agent.py`) e integrações externas (`google_tools.py`).

## Integrações

- **Groq API com GPT-OSS:** interpreta a pergunta e decide se precisa chamar uma ferramenta, usando o SDK OpenAI compatível.
- **Google Custom Search JSON API:** busca páginas externas sob demanda. Configure uma API key e um Programmable Search Engine; a API pode exigir ativação/cobrança conforme a conta Google.
- **Google Sheets API:** registra data/hora, pergunta e resposta na primeira aba da planilha, com OAuth de usuário.
- **Google Docs API:** acrescenta pergunta e resposta sem sintaxe Markdown a um documento existente, com títulos formatados.

## Fluxo de atendimento e painel

1. A pessoa consulta o FAQ e vê a resposta em um modal.
2. Se a resposta resolver a dúvida, seleciona **Sim**; nenhum chamado é aberto.
3. Se não resolver, seleciona **Não, abrir chamado**, informa nome e e-mail e confirma. O GPT classifica a solicitação por categoria e prioridade e grava o chamado com os dados do solicitante.
4. A aba **Dashboard de chamados** resume volumes, permite filtrar por status/categoria, buscar solicitações e atualizar o andamento.

O painel usa a primeira aba da planilha. Ele mantém as três colunas existentes e acrescenta `Categoria`, `Prioridade`, `Status`, `Útil?`, `ID do chamado`, `Solicitante` e `E-mail` nas colunas D:J. Registros históricos sem status continuam preservados e não aparecem como chamados no painel.

## Preparar o ambiente

1. Crie e ative um ambiente virtual: `python -m venv .venv` e `\.venv\Scripts\Activate.ps1` (Windows).
2. Instale as dependências: `pip install -r requirements.txt`.
3. Copie `.env.example` para `.env` e preencha as chaves e IDs.
4. No Google Cloud Console, ative Google Sheets API e Google Docs API, configure a tela OAuth e baixe as credenciais do tipo **Aplicativo para computador** como `credentials.json` nesta pasta.
5. Prepare a primeira aba da planilha. O app mantém `Data/Hora`, `Pergunta`, `Resposta` e adiciona as colunas de classificação quando o primeiro chamado é aberto.
6. Crie um Google Doc, copie o ID da URL (`/document/d/{ID}/edit`) e configure `GOOGLE_DOCS_ID` no `.env`.
7. Apague `token.json` e execute novamente para autorizar o novo escopo do Docs. O app acrescentará as consultas ao documento existente.
8. Execute `streamlit run main.py`.

## Base de conhecimento

O conteúdo em `data/faq.md` é a referência local do agente. Revise e substitua o exemplo pelas respostas aprovadas do arquivo **FAQ de Suporte TI - Hardware e Software.pdf** antes de uso institucional. O modelo usa o texto como fonte de consulta, não como instruções executáveis.

## Segurança

Não versionar `.env`, `credentials.json` nem `token.json`. A chave Groq e a chave Google são lidas do ambiente. O acesso ao Sheets e Docs usa OAuth. As orientações de suporte devem ser validadas pela equipe responsável.
