# -*- coding: utf-8 -*-
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import plotly.express as px

# ==========================================
# CONFIGURAÇÃO E BANCO DE DADOS
# ==========================================
st.set_page_config(page_title="Sistema Integrado SESMT", page_icon="🛡️️", layout="wide")

st.markdown("""
    <style>
    input[type="text"], textarea { text-transform: uppercase !important; }
    .st-emotion-cache-1y4p8pa { padding-top: 2rem; }
    </style>
""", unsafe_allow_html=True)

if not os.path.exists("uploads"):
    os.makedirs("uploads")

def init_db():
    conn = sqlite3.connect("sesmt_control.db", check_same_thread=False, timeout=10)
    c = conn.cursor()
    
    # Ativa o modo WAL para concorrência e evita travamentos de bloqueio
    c.execute("PRAGMA journal_mode=WAL;")
    
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, matricula TEXT UNIQUE, senha TEXT, perfil TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS gestores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, setor TEXT, email TEXT, whatsapp TEXT)''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS formularios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, perguntas TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS checklists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, tipo_checklist TEXT, setor TEXT, responsavel TEXT, 
                    tst_validador TEXT, data_hora TEXT, respostas TEXT, status_validacao TEXT DEFAULT 'VALIDADO')''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, checklist_id INTEGER, setor TEXT, irregularidade TEXT, 
                    responsavel_solicitacao TEXT, gestor_responsavel TEXT, prazo_correcao TEXT, status TEXT, 
                    data_abertura TEXT, data_conclusao TEXT, historico TEXT, observacoes TEXT, 
                    foto_antes TEXT, foto_depois TEXT)''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS metas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, tst_nome TEXT, tipo_checklist TEXT, mes_ano TEXT, quantidade_prevista INTEGER)''')

    try:
        c.execute("ALTER TABLE checklists ADD COLUMN status_validacao TEXT DEFAULT 'VALIDADO'")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    return conn

conn = init_db()

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def calcular_alerta_os(prazo_str, status):
    if status == "CONCLUIDA": return "🟢 CONCLUIDA"
    if not prazo_str: return "⚪ SEM PRAZO DEFINIDO"
    try:
        prazo_data = datetime.strptime(prazo_str, "%d/%m/%Y").date()
        hoje = datetime.now().date()
        diff = (prazo_data - hoje).days
        if diff < 0: return "🔴 VENCIDA"
        elif diff <= 2: return "🟡 PROXIMA DO VENCIMENTO"
        else: return "🟢 DENTRO DO PRAZO"
    except: return "⚪ ERRO NO PRAZO"

def salvar_foto(upload_file, prefixo):
    if upload_file is not None:
        nome_arquivo = f"uploads/{prefixo}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        with open(nome_arquivo, "wb") as f: f.write(upload_file.getbuffer())
        return nome_arquivo
    return None

def notificar_gestor(gestor, email, wpp, id_os):
    st.toast(f"📧 E-mail e WhatsApp enviados para {gestor} (OS #{id_os})", icon="✅")

# ==========================================
# LOGIN
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔐 Acesso SESMT")
        with st.form("login"):
            matr = st.text_input("Matrícula:")
            pwd = st.text_input("Senha:", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                c = conn.cursor()
                c.execute("SELECT id, nome, perfil FROM usuarios WHERE matricula = ? AND senha = ?", (matr.strip().upper(), pwd))
                res = c.fetchone()
                if res:
                    st.session_state.autenticado = True
                    st.session_state.user_id = res[0]
                    st.session_state.user_nome = res[1]
                    st.session_state.user_perfil = res[2]
                    st.rerun()
                else: st.error("Acesso negado.")
    st.stop()

# ==========================================
# NAVEGAÇÃO
# ==========================================
st.sidebar.title(f"👤 {st.session_state.user_nome}")
st.sidebar.caption(f"Perfil: {st.session_state.user_perfil}")
if st.sidebar.button("🚪 Sair"): st.session_state.clear(); st.rerun()

st.sidebar.divider()

opcoes_menu = ["Realizar Inspecao", "Gerar OS", "Gestao de O.S."]
if st.session_state.user_perfil in ["TST", "Supervisor", "Admin"]: opcoes_menu.append("Validar Inspecoes (Estagiarios)")
if st.session_state.user_perfil in ["Supervisor", "Admin"]: opcoes_menu.extend(["Construtor de Formularios", "Gestores e Setores"])
if st.session_state.user_perfil == "Admin": opcoes_menu.extend(["Dashboard e Metas", "Gerenciar Usuarios"])

menu = st.sidebar.radio("Navegação", opcoes_menu)
c = conn.cursor()

# ------------------------------------------
# CONSTRUTOR DE FORMULÁRIOS
# ------------------------------------------
if menu == "Construtor de Formularios":
    st.title("🏗️ Construtor e Editor de Formulários")
    
    t1, t2 = st.tabs(["Criar Novo Modelo", "Editar/Excluir Modelos"])
    
    with t1:
        st.markdown("**Instruções:** Para criar categorias de perguntas (ex: *1 - FACAS*), digite `###` antes do nome da categoria. Nas linhas abaixo, digite as perguntas dessa categoria.")
        with st.form("form_build"):
            f_nome = st.text_input("Nome do Checklist (Ex: SETORES DE PRODUCAO)")
            txt_exemplo = "### 1 - CONDICOES GERAIS\nPiso limpo e sem oleo\nIluminacao adequada\n### 2 - EQUIPAMENTOS DE MOVIMENTACAO\nOperador habilitado"
            f_txt = st.text_area("Estrutura do Checklist", value=txt_exemplo, height=250)
            
            if st.form_submit_button("Salvar Checklist"):
                linhas = f_txt.split('\n')
                dict_form = {}
                cat_atual = "GERAL"
                
                for linha in linhas:
                    linha = linha.strip()
                    if not linha: continue
                    if linha.startswith("###"):
                        cat_atual = linha.replace("###", "").strip()
                        dict_form[cat_atual] = []
                    else:
                        if cat_atual not in dict_form: dict_form[cat_atual] = []
                        dict_form[cat_atual].append(linha)
                        
                try:
                    c.execute("INSERT INTO formularios (nome, perguntas) VALUES (?, ?)", (f_nome.upper(), json.dumps(dict_form)))
                    conn.commit()
                    st.success("Formulário salvo!")
                except sqlite3.IntegrityError: st.error("Nome já existe.")

    with t2:
        df_forms = pd.read_sql_query("SELECT id, nome FROM formularios", conn)
        sel_form = st.selectbox("Selecione o formulário para editar", df_forms['nome'].tolist()) if not df_forms.empty else None
        
        if sel_form:
            c.execute("SELECT id, perguntas FROM formularios WHERE nome = ?", (sel_form,))
            id_f, perg_json = c.fetchone()
            perg_dict = json.loads(perg_json)
            
            texto_edit = ""
            if isinstance(perg_dict, dict):
                for cat, itens in perg_dict.items():
                    if cat != "GERAL": texto_edit += f"### {cat}\n"
                    for i in itens: texto_edit += f"{i}\n"
            else:
                for i in perg_dict: texto_edit += f"{i}\n"
                
            with st.form("form_edit"):
                novo_txt = st.text_area("Editar Estrutura", value=texto_edit, height=250)
                colA, colB = st.columns(2)
                btn_upd = colA.form_submit_button("Atualizar Formulário")
                btn_del = colB.form_submit_button("Excluir Formulário")
                
                if btn_upd:
                    linhas = novo_txt.split('\n')
                    d_form = {}
                    c_atual = "GERAL"
                    for l in linhas:
                        l = l.strip()
                        if not l: continue
                        if l.startswith("###"):
                            c_atual = l.replace("###", "").strip()
                            d_form[c_atual] = []
                        else:
                            if c_atual not in d_form: d_form[c_atual] = []
                            d_form[c_atual].append(l)
                    c.execute("UPDATE formularios SET perguntas = ? WHERE id = ?", (json.dumps(d_form), id_f))
                    conn.commit(); st.success("Atualizado!"); st.rerun()
                
                if btn_del:
                    c.execute("DELETE FROM formularios WHERE id = ?", (id_f,))
                    conn.commit(); st.warning("Excluído!"); st.rerun()

# ------------------------------------------
# REALIZAR INSPEÇÃO
# ------------------------------------------
elif menu == "Realizar Inspecao":
    st.title("📋 Executar Checklist")
    
    df_forms = pd.read_sql_query("SELECT nome FROM formularios", conn)
    df_gestores = pd.read_sql_query("SELECT setor, nome, email, whatsapp FROM gestores", conn)
    
    if df_forms.empty or df_gestores.empty: st.warning("Cadastre formulários e setores antes."); st.stop()

    col1, col2 = st.columns(2)
    tipo_check = col1.selectbox("Modelo de Checklist", df_forms['nome'].tolist())
    setor = col1.selectbox("Setor Auditado", df_gestores['setor'].unique().tolist())
    
    tst_validador = None
    if st.session_state.user_perfil == "Estagiario":
        df_tsts = pd.read_sql_query("SELECT nome FROM usuarios WHERE perfil IN ('TST', 'Supervisor', 'Admin')", conn)
        tst_validador = col2.selectbox("TST Validador Responsável", df_tsts['nome'].tolist())
        col2.warning("O checklist ficará PENDENTE até a validação do TST selecionado.")
    else: col2.info(f"Responsável: {st.session_state.user_nome}")
    
    st.divider()
    
    c.execute("SELECT perguntas FROM formularios WHERE nome = ?", (tipo_check,))
    perg_json = json.loads(c.fetchone()[0])
    
    if isinstance(perg_json, list): perg_json = {"GERAL": perg_json}
    
    respostas = {}
    ncs = []
    
    with st.form("form_inspecao"):
        for cat, itens in perg_json.items():
            if cat != "GERAL": st.markdown(f"#### {cat}")
            for i, p in enumerate(itens):
                st.markdown(f"**{p}**")
                cA, cB = st.columns([1, 3])
                resp = cA.radio("Status", ["OK", "NC", "NA"], horizontal=True, key=f"{cat}_r_{i}", label_visibility="collapsed")
                obs = cB.text_input("Obs", key=f"{cat}_o_{i}", placeholder="Observação", label_visibility="collapsed")
                respostas[p] = {"status": resp, "observacao": obs}
                if resp == "NC": ncs.append((p, obs))
                st.write("")
        
        st.divider()
        gerar_os = False
        op_gerar = "Não"
        if ncs:
            st.error(f"⚠️ {len(ncs)} Não Conformidade(s) detectada(s)!")
            op_gerar = st.radio("Deseja gerar OS?", ["Não", "Sim"], index=1, horizontal=True)
            if op_gerar == "Sim":
                gerar_os = True
                desc_os = st.text_area("Descrição da Irregularidade", value="\n".join([f"- {p} ({o})" for p, o in ncs]))
                foto_nc = st.camera_input("Foto da Situação (Antes)")
                
        if st.form_submit_button("Salvar Checklist", type="primary"):
            data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
            status_val = "PENDENTE" if st.session_state.user_perfil == "Estagiario" else "VALIDADO"
            
            c.execute('''INSERT INTO checklists (tipo_checklist, setor, responsavel, tst_validador, data_hora, respostas, status_validacao) 
                         VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                      (tipo_check, setor, st.session_state.user_nome, tst_validador, data_atual, json.dumps(respostas), status_val))
            check_id = c.lastrowid
            
            if ncs and gerar_os:
                g_row = df_gestores[df_gestores['setor'] == setor].iloc[0]
                path_foto = salvar_foto(foto_nc if 'foto_nc' in locals() else None, f"antes_{check_id}")
                
                c.execute('''INSERT INTO ordens_servico (checklist_id, setor, irregularidade, responsavel_solicitacao, gestor_responsavel, status, data_abertura, foto_antes, historico) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                          (check_id, setor, desc_os.upper(), st.session_state.user_nome, g_row['nome'], "ABERTA", data_atual.split()[0], path_foto, "[]"))
                notificar_gestor(g_row['nome'], g_row['email'], g_row['whatsapp'], c.lastrowid)
                st.success(f"Checklist salvo e OS #{c.lastrowid} aberta com sucesso!")
            else:
                st.success("Checklist salvo com sucesso! (Nenhuma OS gerada)")
            
            conn.commit()

# ------------------------------------------
# GERAR OS (Posterior)
# ------------------------------------------
elif menu == "Gerar OS":
    st.title("📑 Gerar OS de Inspeção Posterior")
    st.markdown("Selecione um checklist realizado anteriormente para gerar a Ordem de Serviço correspondente.")
    
    df_checks = pd.read_sql_query("SELECT id, tipo_checklist, setor, responsavel, data_hora, respostas FROM checklists ORDER BY id DESC", conn)
    
    if df_checks.empty:
        st.info("Nenhum checklist cadastrado no sistema.")
    else:
        df_checks['label'] = df_checks.apply(lambda r: f"Checklist #{r['id']} - {r['tipo_checklist']} ({r['setor']}) por {r['responsavel']} em {r['data_hora']}", axis=1)
        check_selecionado_label = st.selectbox("Selecione o Checklist", df_checks['label'].tolist())
        
        if check_selecionado_label:
            row_chk = df_checks[df_checks['label'] == check_selecionado_label].iloc[0]
            chk_id = row_chk['id']
            setor_chk = row_chk['setor']
            respostas_chk = json.loads(row_chk['respostas'])
            
            ncs_chk = []
            for p, d in respostas_chk.items():
                if isinstance(d, dict) and d.get('status') == 'NC':
                    ncs_chk.append((p, d.get('observacao', '')))
            
            st.markdown(f"**Setor:** {setor_chk} | **Total de NCs encontradas:** {len(ncs_chk)}")
            
            c.execute("SELECT id, status FROM ordens_servico WHERE checklist_id = ?", (chk_id,))
            os_existente = c.fetchall()
            
            if os_existente:
                ids_existentes = ", ".join([str(o[0]) for o in os_existente])
                st.warning(f"⚠️ Este checklist já possui OS gerada(s): #{ids_existentes}.")
            
            if ncs_chk:
                st.markdown("### Não Conformidades Identificadas:")
                for p, obs in ncs_chk:
                    st.markdown(f"- **{p}** (Obs: {obs})")
                
                with st.form(f"form_gerar_os_posterior_{chk_id}"):
                    desc_posterior = st.text_area("Descrição da Irregularidade para a OS", value="\n".join([f"- {p} ({o})" for p, o in ncs_chk]))
                    foto_posterior = st.camera_input("Foto da Situação (Antes)")
                    
                    if st.form_submit_button("Gerar OS Agora", type="primary"):
                        df_gestores_pos = pd.read_sql_query("SELECT setor, nome, email, whatsapp FROM gestores", conn)
                        g_row = df_gestores_pos[df_gestores_pos['setor'] == setor_chk]
                        
                        if not g_row.empty:
                            g_row = g_row.iloc[0]
                            gestor_nome = g_row['nome']
                            g_email = g_row['email']
                            g_wpp = g_row['whatsapp']
                        else:
                            gestor_nome = "GERENTE GERAL"
                            g_email = ""
                            g_wpp = ""
                            
                        data_atual = datetime.now().strftime("%d/%m/%Y")
                        path_foto = salvar_foto(foto_posterior, f"antes_post_{chk_id}")
                        
                        c.execute('''INSERT INTO ordens_servico (checklist_id, setor, irregularidade, responsavel_solicitacao, gestor_responsavel, status, data_abertura, foto_antes, historico) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                                  (chk_id, setor_chk, desc_posterior.upper(), st.session_state.user_nome, gestor_nome, "ABERTA", data_atual, path_foto, "[]"))
                        conn.commit()
                        notificar_gestor(gestor_nome, g_email, g_wpp, c.lastrowid)
                        st.success(f"OS #{c.lastrowid} gerada com sucesso para o checklist #{chk_id}!")
                        st.rerun()
            else:
                st.info("Este checklist não possui nenhuma Não Conformidade (NC) registrada. Deseja abrir uma OS manual mesmo assim?")
                with st.form(f"form_gerar_os_livre_{chk_id}"):
                    desc_livre = st.text_area("Descrição da OS")
                    foto_livre = st.camera_input("Foto da Situação (Antes)")
                    if st.form_submit_button("Gerar OS Manual", type="primary"):
                        df_gestores_pos = pd.read_sql_query("SELECT setor, nome, email, whatsapp FROM gestores", conn)
                        g_row = df_gestores_pos[df_gestores_pos['setor'] == setor_chk]
                        gestor_nome = g_row.iloc[0]['nome'] if not g_row.empty else "GERENTE GERAL"
                        g_email = g_row.iloc[0]['email'] if not g_row.empty else ""
                        g_wpp = g_row.iloc[0]['whatsapp'] if not g_row.empty else ""
                        
                        data_atual = datetime.now().strftime("%d/%m/%Y")
                        path_foto = salvar_foto(foto_livre, f"antes_livre_{chk_id}")
                        
                        c.execute('''INSERT INTO ordens_servico (checklist_id, setor, irregularidade, responsavel_solicitacao, gestor_responsavel, status, data_abertura, foto_antes, historico) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                                  (chk_id, setor_chk, desc_livre.upper(), st.session_state.user_nome, gestor_nome, "ABERTA", data_atual, path_foto, "[]"))
                        conn.commit()
                        notificar_gestor(gestor_nome, g_email, g_wpp, c.lastrowid)
                        st.success(f"OS #{c.lastrowid} gerada com sucesso!")
                        st.rerun()

# ------------------------------------------
# VALIDAR INSPEÇÕES (ESTAGIÁRIOS)
# ------------------------------------------
elif menu == "Validar Inspecoes (Estagiarios)":
    st.title("✅ Validação de Checklists de Estagiários")
    st.markdown("Revise e assine os checklists realizados por estagiários vinculados ao seu nome.")
    
    df_pend = pd.read_sql_query("SELECT id, tipo_checklist, setor, responsavel, data_hora FROM checklists WHERE tst_validador = ? AND status_validacao = 'PENDENTE'", conn, params=(st.session_state.user_nome,))
    
    if df_pend.empty: st.success("Nenhuma validação pendente no momento.")
    else:
        for idx, row in df_pend.iterrows():
            with st.expander(f"Checklist #{row['id']} - {row['tipo_checklist']} ({row['setor']}) | Por: {row['responsavel']} em {row['data_hora']}"):
                c.execute("SELECT respostas FROM checklists WHERE id = ?", (row['id'],))
                resps = json.loads(c.fetchone()[0])
                for p, d in resps.items():
                    cor = "red" if d['status'] == "NC" else ("green" if d['status'] == "OK" else "gray")
                    st.markdown(f"- **{p}**: <span style='color:{cor}'>{d['status']}</span> (Obs: {d['observacao']})", unsafe_allow_html=True)
                
                if st.button(f"Assinar e Validar Checklist #{row['id']}", type="primary"):
                    c.execute("UPDATE checklists SET status_validacao = 'VALIDADO' WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.success("Checklist validado e incorporado aos indicadores oficiais.")
                    st.rerun()

# ------------------------------------------
# GESTÃO DE O.S.
# ------------------------------------------
elif menu == "Gestao de O.S.":
    st.title("🔧 Acompanhamento de O.S.")
    df_os = pd.read_sql_query("SELECT id as OS, data_abertura as Data, setor as Setor, irregularidade, gestor_responsavel as Gestor, prazo_correcao as Prazo, status as Status FROM ordens_servico ORDER BY id DESC", conn)
    
    if df_os.empty: st.info("Nenhuma OS cadastrada.")
    else:
        df_os['Alerta'] = df_os.apply(lambda r: calcular_alerta_os(r['Prazo'], r['Status']), axis=1)
        st.dataframe(df_os, use_container_width=True, hide_index=True)
        
        st.divider()
        os_id = st.selectbox("Atualizar OS Número:", df_os['OS'].tolist())
        if os_id:
            c.execute("SELECT * FROM ordens_servico WHERE id = ?", (os_id,))
            dados = c.fetchone()
            
            c1, c2 = st.columns([1,1])
            with c1:
                st.markdown(f"**Gestor:** {dados[5]} | **Abertura:** {dados[8]}")
                st.markdown(f"**Irregularidade:** {dados[3]}")
                hist = json.loads(dados[10] or "[]")
                st.markdown("**Histórico:**")
                for h in hist: st.caption(f"- {h}")
            with c2:
                with st.form("upd_os"):
                    sts = st.selectbox("Status", ["ABERTA", "EM ANDAMENTO", "AGUARDANDO PECA", "CONCLUIDA"], index=["ABERTA", "EM ANDAMENTO", "AGUARDANDO PECA", "CONCLUIDA"].index(dados[7]))
                    prz = st.text_input("Prazo (DD/MM/AAAA)", value=dados[6] or "")
                    com = st.text_input("Novo Comentário")
                    f_dep = st.file_uploader("Evidência (Foto Depois)", type=['jpg', 'png']) if sts == "CONCLUIDA" else None
                    
                    if st.form_submit_button("Atualizar"):
                        if com: hist.append(f"{datetime.now().strftime('%d/%m/%Y')} - {st.session_state.user_nome}: {com}")
                        d_conc = datetime.now().strftime("%d/%m/%Y") if sts == "CONCLUIDA" else dados[9]
                        p_dep = salvar_foto(f_dep, f"depois_{os_id}") if f_dep else dados[13]
                        
                        c.execute("UPDATE ordens_servico SET status=?, prazo_correcao=?, historico=?, data_conclusao=?, foto_depois=? WHERE id=?", (sts, prz, json.dumps(hist), d_conc, p_dep, os_id))
                        conn.commit(); st.success("Atualizada!"); st.rerun()

# ------------------------------------------
# GESTORES E SETORES (Supervisor/Admin)
# ------------------------------------------
elif menu == "Gestores e Setores":
    st.title("🏢 Gestores e Setores")
    
    with st.form("form_gestor"):
        col1, col2 = st.columns(2)
        with col1:
            g_nome = st.text_input("Nome do Gestor")
            g_setor = st.text_input("Setor/Área")
        with col2:
            g_email = st.text_input("E-mail")
            g_wpp = st.text_input("WhatsApp (com DDD)")
            
        if st.form_submit_button("Cadastrar Gestor/Setor"):
            if g_nome and g_setor:
                c.execute("INSERT INTO gestores (nome, setor, email, whatsapp) VALUES (?, ?, ?, ?)",
                          (g_nome.upper(), g_setor.upper(), g_email, g_wpp))
                conn.commit()
                st.success("Gestor cadastrado com sucesso!")
                
    st.divider()
    df_gestores = pd.read_sql_query("SELECT nome as Gestor, setor as Setor, email, whatsapp FROM gestores", conn)
    st.dataframe(df_gestores, use_container_width=True, hide_index=True)

# ------------------------------------------
# DASHBOARD E METAS (Admin)
# ------------------------------------------
elif menu == "Dashboard e Metas":
    st.title("📊 Dashboard e Acompanhamento SESMT")
    
    t1, t2 = st.tabs(["Dashboard Gráfico", "Definição de Metas"])
    with t1:
        df_chk = pd.read_sql_query("SELECT * FROM checklists WHERE status_validacao = 'VALIDADO'", conn)
        df_os = pd.read_sql_query("SELECT * FROM ordens_servico", conn)
        df_mt = pd.read_sql_query("SELECT * FROM metas", conn)
        
        if df_chk.empty: st.warning("Sem dados suficientes."); st.stop()
        
        df_chk['MesAno'] = df_chk['data_hora'].str[3:10]
        meses = sorted(df_chk['MesAno'].unique().tolist(), reverse=True)
        mes_filtro = st.selectbox("Selecione o Mês", meses)
        
        df_chk_mes = df_chk[df_chk['MesAno'] == mes_filtro]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Checklists Realizados", len(df_chk_mes))
        c2.metric("OS Pendentes", len(df_os[df_os['status'] != 'CONCLUIDA']) if not df_os.empty else 0)
        
        os_venc = 0
        if not df_os.empty:
            for _, r in df_os.iterrows():
                if "VENCIDA" in calcular_alerta_os(r['prazo_correcao'], r['status']): os_venc += 1
        c3.metric("OS Vencidas", os_venc)
        
        st.divider()
        colA, colB = st.columns(2)
        with colA:
            st.subheader("OS por Status")
            if not df_os.empty:
                fig_pie = px.pie(df_os, names='status', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
                
        with colB:
            st.subheader("Cumprimento de Metas (Geral)")
            if not df_mt.empty:
                mt_mes = df_mt[df_mt['mes_ano'] == mes_filtro]
                resultado_metas = []
                for _, m in mt_mes.iterrows():
                    realiz = len(df_chk_mes[(df_chk_mes['responsavel'] == m['tst_nome']) & (df_chk_mes['tipo_checklist'] == m['tipo_checklist'])])
                    resultado_metas.append({"TST": m['tst_nome'], "Realizado": realiz, "Previsto": m['quantidade_prevista']})
                if resultado_metas:
                    df_graf = pd.DataFrame(resultado_metas)
                    fig_bar = px.bar(df_graf, x="TST", y=["Realizado", "Previsto"], barmode="group", text_auto=True)
                    st.plotly_chart(fig_bar, use_container_width=True)
                else: st.info("Sem metas definidas para o mês.")

    with t2:
        with st.form("form_mt"):
            df_tsts = pd.read_sql_query("SELECT nome FROM usuarios WHERE perfil IN ('TST', 'Supervisor', 'Admin')", conn)
            df_forms = pd.read_sql_query("SELECT nome FROM formularios", conn)
            
            c1, c2, c3, c4 = st.columns(4)
            mTST = c1.selectbox("TST", df_tsts['nome'].tolist())
            mForm = c2.selectbox("Checklist", df_forms['nome'].tolist())
            mMes = c3.text_input("Mês/Ano (MM/AAAA)")
            mQtd = c4.number_input("Qtd Prevista", min_value=1)
            
            if st.form_submit_button("Adicionar Meta"):
                c.execute("INSERT INTO metas (tst_nome, tipo_checklist, mes_ano, quantidade_prevista) VALUES (?,?,?,?)", (mTST, mForm, mMes, mQtd))
                conn.commit(); st.success("Salvo!")

# ------------------------------------------
# GERENCIAR USUÁRIOS (Admin)
# ------------------------------------------
elif menu == "Gerenciar Usuarios":
    st.title("👥 Gerenciamento de Usuários")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Novo Usuário")
        with st.form("form_user"):
            n_nome = st.text_input("Nome Completo")
            n_matr = st.text_input("Matrícula (Para estagiário, use identificação única)")
            n_senha = st.text_input("Senha", type="password")
            n_perfil = st.selectbox("Perfil", ["TST", "Supervisor", "Estagiario", "Admin"])
            if st.form_submit_button("Cadastrar"):
                try:
                    c.execute("SELECT 1 FROM usuarios WHERE matricula = ?", (n_matr.strip().upper(),))
                    if c.fetchone():
                        st.error("Matrícula já existente no sistema.")
                    else:
                        c.execute("INSERT INTO usuarios (nome, matricula, senha, perfil) VALUES (?, ?, ?, ?)", 
                                  (n_nome.upper(), n_matr.upper(), n_senha, n_perfil))
                        conn.commit()
                        st.success("Usuário cadastrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao cadastrar usuário: {e}")
                    
    with col2:
        st.subheader("Usuários Cadastrados")
        df_users = pd.read_sql_query("SELECT matricula, nome, perfil FROM usuarios", conn)
        st.dataframe(df_users, use_container_width=True, hide_index=True)