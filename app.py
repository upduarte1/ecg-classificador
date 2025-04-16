import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# 🔐 Conectar às duas planilhas separadas
def conectar_planilhas():
    escopos = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credenciais = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    credenciais = ServiceAccountCredentials.from_json_keyfile_dict(credenciais, escopos)
    cliente = gspread.authorize(credenciais)

    classificacoes_sheet = cliente.open("ECG Classificações").sheet1
    sinais_sheet = cliente.open("ECG Sinais").sheet1  # ou outra aba específica se for diferente
    return classificacoes_sheet, sinais_sheet


# 📥 Carregar os sinais da planilha de sinais
def carregar_sinais(sheet):
    linhas = sheet.get_all_values()
    ecgs = {}
    for linha in linhas:
        if not linha or not linha[0].isdigit():
            continue  # pula linhas vazias ou com headers

        try:
            sinal_id = int(linha[0])
            valores = [int(x) for x in linha[1:] if x.strip() != ""]
            ecgs[sinal_id] = valores
        except Exception as e:
            print(f"Erro ao processar linha {linha[0]}: {e}")
    return ecgs


# 📡 Conectar às planilhas e carregar dados
classificacoes_sheet, sinais_sheet = conectar_planilhas()
ecgs = carregar_sinais(sinais_sheet)

# 🧠 App principal
st.title("Classificador de Sinais ECG")
nome = st.text_input("Identifique-se:", max_chars=50)

if nome:
    registros = classificacoes_sheet.get_all_records()
    ids_classificados = {r['signal_id'] for r in registros if r['cardiologista'] == nome}

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
            if st.button("✅ Normal"):
                selecionar_rotulo("Normal")
        with col2:
            if st.button("⚠️ Arritmia"):
                selecionar_rotulo("Arritmia")
        with col3:
            if st.button("🔥 Fibrilação"):
                selecionar_rotulo("Fibrilação")
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
        st.info("🎉 Você já classificou todos os sinais disponíveis!")
