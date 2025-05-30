import streamlit as st
import boto3
import json
import pandas as pd

# =========================
# PRIMEIRO comando do app
# =========================
st.set_page_config(page_title="Escola Tecnologia para Todos", page_icon="🎓")

# =========================
# Configuração da AWS Bedrock
# =========================
session = boto3.Session(profile_name="default")  # Verifique o nome do perfil AWS
client = session.client("bedrock-runtime", region_name="us-east-1")

# =================================
# Carregar dados dos arquivos CSV
# =================================
try:
    alunos_df = pd.read_csv("alunos.csv")
    cursos_df = pd.read_csv("cursos.csv")
except Exception as e:
    st.error(f"Erro ao carregar os dados: {e}")
    st.stop()

# =================================================
# Função para gerar respostas com base nos dados
# =================================================
def gerar_resposta(user_input):
    user_input = user_input.lower()

    if "quais cursos" in user_input or "cursos oferecidos" in user_input:
        cursos = cursos_df['course_name'].tolist()
        return "Nós oferecemos os seguintes cursos gratuitos e online:\n" + "\n".join([f"- {c}" for c in cursos])

    if "duração" in user_input and "devops" in user_input:
        row = cursos_df[cursos_df['course_name'].str.contains("devops", case=False)]
        if not row.empty:
            return f"O curso de DevOps com AWS tem duração de {row.iloc[0]['duration_weeks']} semanas."
        return "Não encontrei informações sobre esse curso."

    if "banco de dados" in user_input and "iniciante" in user_input:
        row = cursos_df[(cursos_df['course_name'].str.contains("banco", case=False)) & 
                        (cursos_df['level'].str.contains("básico|iniciante", case=False))]
        if not row.empty:
            return f"Sim! Temos o curso **{row.iloc[0]['course_name']}**, com duração de {row.iloc[0]['duration_weeks']} semanas, voltado para iniciantes."
        return "Não temos curso de Banco de Dados para iniciantes."

    if "metodologias ágeis" in user_input:
        row = cursos_df[cursos_df['course_name'].str.contains("metodologias", case=False)]
        if not row.empty:
            return f"O curso de Metodologias Ágeis e Soft Skills tem duração de {row.iloc[0]['duration_weeks']} semanas e é para todos os níveis."
        return "Curso de Metodologias Ágeis não encontrado."

    if "emprego" in user_input or "conseguiram emprego" in user_input:
        empregados = alunos_df[alunos_df['current_job'].notnull()]
        if not empregados.empty:
            exemplos = "\n".join([f"- {row['name']} trabalha como {row['current_job']}" for _, row in empregados.iterrows()])
            return f"Sim! Alguns alunos conseguiram emprego após os cursos:\n{exemplos}"
        return "Ainda não temos registros públicos de alunos empregados."

   
    if "regiões" in user_input or "de onde vêm os alunos" in user_input:
        locais = alunos_df['region'].dropna().unique().tolist()
        return f"Nossos alunos vêm de diversas regiões do Brasil, como: {', '.join(locais)}."

    if "inscrever" in user_input:
        return "Você pode se inscrever acessando nosso site e preenchendo o formulário de inscrição do curso desejado. 📄"

    if "certificado" in user_input:
        return "Sim! Todos os cursos oferecem certificado após a conclusão. 🎓"

    if "pagos" in user_input:
        return "Não! Todos os nossos cursos são 100% gratuitos. 🙌"

    if "online" in user_input:
        return "Sim, nossos cursos são totalmente online! Você pode estudar de onde estiver. 💻"

    # Se não encontrar nada, retorna None para utilizar o modelo Bedrock
    return None

# ===============================================
# Função para chamada ao Claude v2 via Bedrock
# ===============================================
def call_bedrock_model(messages):
    filtered_messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in messages if msg["role"] in ["user", "assistant"]
    ]

    payload = {
        "messages": filtered_messages,
        "max_tokens": 210,
        "anthropic_version": "bedrock-2023-05-31",
        "temperature": 0.3,
        "top_p": 0.8,
        
    }

    try:
        response = client.invoke_model_with_response_stream(
            modelId="anthropic.claude-v2",
            body=json.dumps(payload).encode("utf-8"),
            contentType="application/json",
            accept="application/json"
        )
        output = []
        stream = response.get("body")
        for event in stream:
            chunk = event.get("chunk")
            if chunk:
                chunk_data = json.loads(chunk.get("bytes").decode())
                if chunk_data.get("type") == "content_block_delta":
                    delta = chunk_data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        output.append(delta.get("text", ""))
        return "".join(output)
    except Exception as e:
        return f"Erro ao chamar o modelo: {e}"

# =========================
# Interface do Chatbot
# =========================
st.title("🤖 Chat - Escola Tecnologia para Todos")

st.markdown("""
💬 **Bem-vindo(a) à nossa escola!**
Esta é uma iniciativa social que oferece **cursos 100% gratuitos e online** para pessoas em **situação de vulnerabilidade social**, com foco em:

- Computação em Nuvem AWS
- Front-End, Back-End
- Banco de Dados, DevOps
- Metodologias Ágeis & Soft Skills
- Empregabilidade com casos reais de sucesso!

Digite sua pergunta abaixo e converse com nosso assistente virtual. 👇
""")

with st.expander("👩‍🎓 Alunos e histórias de sucesso"):
    st.dataframe(alunos_df)

with st.expander("📚 Cursos disponíveis"):
    st.dataframe(cursos_df)

# Histórico de conversa
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Entrada do usuário
user_input = st.text_input("Digite sua pergunta aqui 👇", key="pergunta")

if st.button("Enviar") and user_input.strip():
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    resposta = gerar_resposta(user_input)

    if resposta is None:
        with st.spinner("Consultando o assistente..."):
            resposta = call_bedrock_model([{"role": "user", "content": user_input}])

    st.session_state.chat_history.append({"role": "assistant", "content": resposta})

# Mostrar conversa
st.markdown("---")
st.subheader("🗨️ Conversa")
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.write(f"👤 **Você:** {msg['content']}")
    elif msg["role"] == "assistant":
        st.write(f"🤖 **Assistente:** {msg['content']}")

