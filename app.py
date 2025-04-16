import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

USUARIOS = {
    "joao": "1234",
    "maria": "abcd",
    "luisa": "senha123"
}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""

if not st.session_state.autenticado:
    st.title("🔐 Login")

    with st.form("login_form"):
        usuario = st.text_input("Usuário").strip().lower()
        senha = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")

        if submit:
            if usuario in USUARIOS and senha == USUARIOS[usuario]:
                st.session_state.autenticado = True
                st.session_state.usuario = usuario
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
else:
    nome = st.session_state.usuario
    st.sidebar.success(f"✅ Logado como: {nome}")
    # 👉 Aqui segue o restante da lógica do seu app normalmente


# 🔐 Conectar às duas planilhas separadas
def connect_sheets():
    escopos = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credenciais = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    credenciais = ServiceAccountCredentials.from_json_keyfile_dict(credenciais, escopos)
    cliente = gspread.authorize(credenciais)
    
    classificacoes_sheet = cliente.open("ECG Classificações").sheet1
    sinais_sheet = cliente.open("ECG Dados").sheet1  # ou o nome correto da aba
    return classificacoes_sheet, sinais_sheet

# 📥 Carregar os sinais da planilha de sinais
def carregar_sinais(sheet):
    registros = sheet.get_all_records()
    ecgs = {}
    for linha in registros:
        try:
            signal_id = int(linha["signal_id"])
            ecg_str = linha["ecg_signal"]
            valores = [float(v.strip()) for v in ecg_str.split(",") if v.strip()]
            ecgs[signal_id] = valores
        except Exception as e:
            st.warning(f"Erro ao processar sinal {linha}: {e}")
    return ecgs

# 📡 Conectar às planilhas e carregar dados
classificacoes_sheet, sinais_sheet = connect_sheets()
ecgs = carregar_sinais(sinais_sheet)

# 🧠 App principal
st.title("Classificador de Sinais ECG")
nome = st.text_input("Introduza o seu nome:", max_chars=50)

if nome:
    registros = classificacoes_sheet.get_all_records()
    ids_classificados = {r['signal_id'] for r in registros if r['cardiologista'] == nome}

    total_sinais = len(ecgs)
    num_classificados = len(ids_classificados)
    st.info(f"📊 Sinais classificados: {num_classificados} / {total_sinais}.")

    progresso = num_classificados / total_sinais
    st.progress(progresso)
            
    sinais_disponiveis = [k for k in ecgs if k not in ids_classificados]

    if sinais_disponiveis:
        sinal_id = sinais_disponiveis[0]
        st.subheader(f"Sinal ID: {sinal_id}")
        st.line_chart(ecgs[sinal_id])

        st.write("Classifique o sinal:")
        col1, col2, col3, col4 = st.columns(4)

        def classificar(rotulo):
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            classificacoes_sheet.append_row([sinal_id, nome, rotulo, agora])
            st.success(f"Sinal {sinal_id} classificado como '{rotulo}'!")
            st.rerun()

        if "rotulo_temp" not in st.session_state:
            st.session_state.rotulo_temp = None
        if "comentario_temp" not in st.session_state:
            st.session_state.comentario_temp = ""

        def selecionar_rotulo(rotulo):
            st.session_state.rotulo_temp = rotulo

        with col1:
            if st.button("⚠️ Fibrilhação"):
                selecionar_rotulo("Fibrilhação")
        with col2:
            if st.button("✅ Normal"):
                selecionar_rotulo("Normal")
        with col3:
            if st.button("⚡ Ruidoso"):
                selecionar_rotulo("Ruidoso")
        with col4:
            if st.button("❓ Outro"):
                selecionar_rotulo("Outro")

        if st.session_state.rotulo_temp:
            st.write(f"Você selecionou: **{st.session_state.rotulo_temp}**")
            st.session_state.comentario_temp = st.text_input("Comentário (opcional):", value=st.session_state.comentario_temp)

            if st.button("Confirmar classificação"):
                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                classificacoes_sheet.append_row([
                    sinal_id,
                    nome,
                    st.session_state.rotulo_temp,
                    agora,
                    st.session_state.comentario_temp
                ])
                st.success(f"Sinal {sinal_id} classificado como '{st.session_state.rotulo_temp}'!")
                st.session_state.rotulo_temp = None
                st.session_state.comentario_temp = ""
                st.rerun()

    else:
        st.info("Você já classificou todos os sinais disponíveis! Obrigado!")
