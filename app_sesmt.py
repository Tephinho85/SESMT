import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os
import io
import tempfile
from fpdf import FPDF

# ==========================================
# CONFIGURAÇÃO DE BANCO DE DADOS E PASTAS
# ==========================================
if not os.path.exists("uploads"):
    os.makedirs("uploads")

def init_db():
    conn = sqlite3.connect("sesmt_control.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS setores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS checklists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT,
                    setor TEXT,
                    responsavel TEXT,
                    data_hora TEXT,
                    conformidade_geral REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checklist_id INTEGER,
                    setor TEXT,
                    descricao TEXT,
                    status TEXT,
                    data_abertura TEXT,
                    imagem_path TEXT)''')
    conn.commit()
    return conn

# ==========================================
# GERAÇÃO DE PDF E EXCEL
# ==========================================
def gerar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Ordens_Servico')
    return output.getvalue()

def gerar_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Relatorio de Inspecao e Ordens de Servico - SESMT", ln=True, align="C")
    pdf.ln(10)
    
    for _, row in df.iterrows():
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, f"OS: {row['OS_Num']} | Status: {row['Status']} | Setor: {row['Setor']}", ln=True)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 8, f"Data Abertura: {row['Data']}", ln=True)
        
        # Substitui caracteres não suportados pela fonte padrão do FPDF
        desc = str(row['Descricao']).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, f"Descricao: {desc}")
        pdf.ln(5)
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            bytes_pdf = f.read()
    os.remove(tmp.name)
    return bytes_pdf

# ==========================================
# INTERFACE DO USUÁRIO
# ==========================================
st.set_page_config(page_title="Sistema Integrado SESMT", layout="wide")

# CSS para forçar a digitação em Maiúsculo visualmente
st.markdown("""
    <style>
    input[type="text"], textarea {
        text-transform: uppercase !important;
    }
    </style>
""", unsafe_allow_html=True)

conn = init_db()

st.sidebar.title("Menu SESMT")
menu = st.sidebar.radio("Navegação", ["Realizar Inspeção", "Gestão de O.S.", "Dashboard e Relatórios", "Cadastro de Setores"])

if menu == "Cadastro de Setores":
    st.title("🏢 Cadastro de Setores")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Cadastrar Novo Setor**")
        with st.form("form_novo_setor", clear_on_submit=True):
            # Formata em UpperCase no backend também
            novo_setor = st.text_input("Nome do Novo Setor:")
            if st.form_submit_button("Salvar Setor"):
                if novo_setor.strip():
                    setor_formatado = novo_setor.strip().upper()
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO setores (nome) VALUES (?)", (setor_formatado,))
                        conn.commit()
                        st.success(f"Setor '{setor_formatado}' cadastrado com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Este setor já está cadastrado.")
                else:
                    st.warning("Preencha o campo com o nome do setor.")
                
    with col2:
        st.subheader("Setores Cadastrados")
        df_setores = pd.read_sql_query("SELECT id, nome FROM setores ORDER BY nome", conn)
        if not df_setores.empty:
            st.dataframe(df_setores, hide_index=True, use_container_width=True)

elif menu == "Realizar Inspeção":
    st.title("📋 Nova Inspeção de Área")
    df_setores = pd.read_sql_query("SELECT nome FROM setores ORDER BY nome", conn)
    lista_setores = df_setores['nome'].tolist() if not df_setores.empty else ["(Nenhum setor cadastrado)"]
    
    col1, col2 = st.columns(2)
    with col1:
        tipo_checklist = st.selectbox("Tipo de Checklist", ["Áreas de Produção", "Desossa", "Evaporadores", "Equipamentos de Emergência"])
        responsavel = st.text_input("Matrícula/Nome do Responsável SESMT")
    with col2:
        setor = st.selectbox("Setor Inspecionado", lista_setores)
        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
        st.write(f"**Data/Hora:** {data_atual}")

    st.divider()
    st.write("*(Perguntas do checklist ocultadas para focar na mecânica do sistema...)*")
    f1 = st.radio("1.1 Item inspecionado exemplo", ["OK", "NC", "NA"], horizontal=True)

    st.divider()
    st.subheader("Abertura Automática de O.S. e Evidências")
    descricao_nc = st.text_area("Descrição da Irregularidade / Motivo da OS")
    
    col_img1, col_img2 = st.columns(2)
    with col_img1:
        foto_camera = st.camera_input("Tirar foto da irregularidade na hora")
    with col_img2:
        imagem_upload = st.file_uploader("Ou escolha uma foto da galeria", type=["jpg", "png", "jpeg"])
    
    gerar_os = st.checkbox("Gerar Ordem de Serviço para a Manutenção?")

    if st.button("Salvar Checklist", type="primary"):
        if setor == "(Nenhum setor cadastrado)":
            st.error("Por favor, cadastre um setor primeiro na aba 'Cadastro de Setores'.")
        elif responsavel.strip() and setor:
            c = conn.cursor()
            
            # Aplicação do .upper() nos campos de texto livre da inspeção
            resp_formatado = responsavel.strip().upper()
            desc_formatada = descricao_nc.strip().upper() if descricao_nc else ""
            
            c.execute("INSERT INTO checklists (tipo, setor, responsavel, data_hora, conformidade_geral) VALUES (?, ?, ?, ?, ?)", 
                      (tipo_checklist, setor, resp_formatado, data_atual, 100.0))
            checklist_id = c.lastrowid
            
            if gerar_os and desc_formatada:
                caminho_imagem = None
                imagem_final = foto_camera if foto_camera else imagem_upload
                
                if imagem_final is not None:
                    nome_arquivo = f"uploads/nc_{checklist_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                    with open(nome_arquivo, "wb") as f:
                        f.write(imagem_final.getbuffer())
                    caminho_imagem = nome_arquivo

                c.execute("INSERT INTO ordens_servico (checklist_id, setor, descricao, status, data_abertura, imagem_path) VALUES (?, ?, ?, ?, ?, ?)",
                          (checklist_id, setor, desc_formatada, "Aberta", data_atual, caminho_imagem))
                
            conn.commit()
            st.success("Checklist registrado com sucesso!")
        else:
            st.warning("Preencha o Responsável e o Setor antes de salvar.")

elif menu == "Gestão de O.S.":
    st.title("🔧 Acompanhamento de Ordens de Serviço")
    df_os = pd.read_sql_query("SELECT id as OS_Num, data_abertura as Data, setor as Setor, descricao as Descricao, status as Status, imagem_path FROM ordens_servico", conn)
    
    if not df_os.empty:
        st.dataframe(df_os.drop(columns=['imagem_path']), use_container_width=True)
        st.divider()
        st.subheader("Detalhes e Atualização da O.S.")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            os_selecionada = st.selectbox("Número da O.S.", df_os['OS_Num'].tolist())
        with col2:
            novo_status = st.selectbox("Novo Status", ["Aberta", "Em Andamento", "Aguardando Peça", "Concluída"])
        
        linha_os = df_os[df_os['OS_Num'] == os_selecionada].iloc[0]
        caminho_img = linha_os['imagem_path']
        
        with col3:
            st.write("**Evidência Fotográfica:**")
            if caminho_img and os.path.exists(caminho_img):
                st.image(caminho_img, caption=f"Foto atrelada à O.S. {os_selecionada}", width=300)
            else:
                st.info("Nenhuma imagem registrada para esta O.S.")
            
        if st.button("Atualizar Status da O.S."):
            c = conn.cursor()
            c.execute("UPDATE ordens_servico SET status = ? WHERE id = ?", (novo_status, os_selecionada))
            conn.commit()
            st.success(f"O.S. {os_selecionada} atualizada para '{novo_status}'!")
            st.rerun()
    else:
        st.info("Nenhuma Ordem de Serviço registrada no momento.")

elif menu == "Dashboard e Relatórios":
    st.title("📊 Relatórios e Indicadores do SESMT")
    
    df_os = pd.read_sql_query("SELECT id as OS_Num, data_abertura as Data, setor as Setor, descricao as Descricao, status as Status FROM ordens_servico", conn)
    df_check = pd.read_sql_query("SELECT * FROM checklists", conn)
    
    if not df_os.empty:
        col_excel, col_pdf, espaco = st.columns([1, 1, 2])
        
        with col_excel:
            excel_bytes = gerar_excel(df_os)
            st.download_button(label="📥 Exportar OS para Excel", data=excel_bytes, file_name="Relatorio_OS.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
        with col_pdf:
            pdf_bytes = gerar_pdf(df_os)
            st.download_button(label="📄 Exportar OS para PDF", data=pdf_bytes, file_name="Relatorio_OS.pdf", mime="application/pdf")
            
        st.divider()
        
    if not df_check.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Checklists (Mês)", len(df_check))
        total_os_abertas = len(df_os[df_os['Status'] != 'Concluída']) if not df_os.empty else 0
        col2.metric("O.S. Pendentes", total_os_abertas)
        col3.metric("Setor Mais Inspecionado", df_check['setor'].mode()[0] if not df_check['setor'].mode().empty else "N/A")
        
        st.subheader("Histórico Recente de Inspeções")
        st.dataframe(df_check[['data_hora', 'tipo', 'setor', 'responsavel']], use_container_width=True)
    else:
        st.info("Nenhum dado consolidado para gerar gráficos ainda.")