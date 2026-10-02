import sqlite3
import json
from datetime import datetime, timedelta

def popular_banco_dados(db_name="sesmt_control.db"):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    print("Criando/Verificando estrutura das tabelas...")

    # 1. Tabela de Usuarios
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT,
                    matricula TEXT UNIQUE,
                    senha TEXT,
                    perfil TEXT)''')

    # 2. Tabela de Gestores / Setores
    c.execute('''CREATE TABLE IF NOT EXISTS gestores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT,
                    setor TEXT,
                    email TEXT,
                    whatsapp TEXT)''')

    # 3. Tabela de Formularios
    c.execute('''CREATE TABLE IF NOT EXISTS formularios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE,
                    perguntas TEXT)''')

    # 4. Tabela de Checklists
    c.execute('''CREATE TABLE IF NOT EXISTS checklists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_checklist TEXT,
                    setor TEXT,
                    responsavel TEXT,
                    tst_validador TEXT,
                    data_hora TEXT,
                    respostas TEXT)''')

    # 5. Tabela de Ordens de Servico (OS)
    c.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checklist_id INTEGER,
                    setor TEXT,
                    irregularidade TEXT,
                    responsavel_solicitacao TEXT,
                    gestor_responsavel TEXT,
                    prazo_correcao TEXT,
                    status TEXT,
                    data_abertura TEXT,
                    data_conclusao TEXT,
                    historico TEXT,
                    observacoes TEXT,
                    foto_antes TEXT,
                    foto_depois TEXT)''')

    # 6. Tabela de Metas
    c.execute('''CREATE TABLE IF NOT EXISTS metas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tst_nome TEXT,
                    tipo_checklist TEXT,
                    mes_ano TEXT,
                    quantidade_prevista INTEGER)''')

    # Limpando registros antigos
    for tbl in ['usuarios', 'gestores', 'formularios', 'checklists', 'ordens_servico', 'metas']:
        c.execute(f"DELETE FROM {tbl}")

    print("Inserindo dados de teste...")

    # 1. USUARIOS
    usuarios = [
        ("ADMINISTRADOR SISTEMA", "0000", "1234", "Admin"),
        ("CARLOS SUPERVISOR", "1111", "1234", "Supervisor"),
        ("JOAO PEDRO TST", "2222", "1234", "TST"),
        ("MARIA SILVA TST", "3333", "1234", "TST"),
        ("LUCAS ESTAGIARIO", "ESTAG01", "1234", "Estagiario")
    ]
    c.executemany("INSERT INTO usuarios (nome, matricula, senha, perfil) VALUES (?, ?, ?, ?)", usuarios)

    # 2. GESTORES E SETORES
    gestores = [
        ("MARCOS ANTONIO", "DESOSSA", "marcos.desossa@empresa.com.br", "(27) 99999-1001"),
        ("ROBERTO ALMEIDA", "EVAPORADORES", "roberto.refrigeracao@empresa.com.br", "(27) 99999-1002"),
        ("FERNANDA SOUZA", "AREAS DE PRODUCAO", "fernanda.producao@empresa.com.br", "(27) 99999-1003"),
        ("EDSON SILVA", "EMBALAGEM", "edson.embalagem@empresa.com.br", "(27) 99999-1004"),
        ("PATRICIA LIMA", "ALMOXARIFADO", "patricia.almox@empresa.com.br", "(27) 99999-1005")
    ]
    c.executemany("INSERT INTO gestores (nome, setor, email, whatsapp) VALUES (?, ?, ?, ?)", gestores)

    # 3. FORMULARIOS DE CHECKLIST
    forms = [
        ("CHECKLIST DE DESOSSA", json.dumps([
            "Facas armazenadas em local adequado",
            "Empregados utilizando luva de aco e EPIs de prevencao de corte",
            "Protecoes e dispositivos de seguranca de maquinas instalados e funcionando",
            "Piso limpo e sem condicoes que favorecam escorregamentos",
            "Quadros eletricos identificados e sem fios expostos",
            "Extintores no local correto e desobstruidos"
        ])),
        ("CHECKLIST DE EVAPORADORES", json.dumps([
            "Evaporador apresenta-se limpo, sem acumulo excessivo de sujeira",
            "Hastes que sustentam o evaporador estao integras",
            "Helices encontram-se integras, sem trincas ou quebras",
            "Cabos eletricos encontram-se protegidos e sem danos aparentes",
            "Nao ha risco aparente de queda de componentes do evaporador",
            "Fluxo de ar encontra-se adequado e sem ruidos anormais"
        ])),
        ("CHECKLIST DE AREAS DE PRODUCAO", json.dumps([
            "Piso limpo, sem agua, oleo ou residuos",
            "Iluminacao e ventilacao adequadas",
            "Equipamentos de movimentacao (paleteiras/empilhadeiras) em boas condicoes",
            "Protecoes de correias, polias e partes moveis de maquinas (NR 12)",
            "Quadros eletricos trancados e identificados (NR 10)",
            "Rotas de fuga e saidas de emergencia desobstruidas (NR 23)"
        ])),
        ("EQUIPAMENTOS DE EMERGENCIA", json.dumps([
            "Extintores dentro da validade e pressurizados",
            "Mangueiras de hidrante acopladas e sem vazamentos",
            "Iluminacao de emergencia testada e operacional",
            "Alarmes de incendio operacionais",
            "Chuveiros e lava-olhos de emergencia desobstruidos e limpos"
        ]))
    ]
    c.executemany("INSERT INTO formularios (nome, perguntas) VALUES (?, ?)", forms)

    # 4. CHECKLISTS PREENCHIDOS
    hoje = datetime.now()
    d1 = (hoje - timedelta(days=12)).strftime("%d/%m/%Y %H:%M")
    d2 = (hoje - timedelta(days=8)).strftime("%d/%m/%Y %H:%M")
    d3 = (hoje - timedelta(days=3)).strftime("%d/%m/%Y %H:%M")
    d4 = hoje.strftime("%d/%m/%Y %H:%M")

    resp_desossa = json.dumps({
        "Facas armazenadas em local adequado": {"status": "OK", "observacao": ""},
        "Empregados utilizando luva de aco e EPIs de prevencao de corte": {"status": "OK", "observacao": ""},
        "Protecoes e dispositivos de seguranca de maquinas instalados e funcionando": {"status": "NC", "observacao": "Protecao lateral da serra fita solta"},
        "Piso limpo e sem condicoes que favorecam escorregamentos": {"status": "OK", "observacao": ""},
        "Quadros eletricos identificados e sem fios expostos": {"status": "OK", "observacao": ""},
        "Extintores no local correto e desobstruidos": {"status": "OK", "observacao": ""}
    })

    resp_evaporador = json.dumps({
        "Evaporador apresenta-se limpo, sem acumulo excessivo de sujeira": {"status": "OK", "observacao": ""},
        "Hastes que sustentam o evaporador estao integras": {"status": "NC", "observacao": "Haste de sustentacao do evaporador 03 com corrosao excessiva"},
        "Helices encontram-se integras, sem trincas ou quebras": {"status": "OK", "observacao": ""},
        "Cabos eletricos encontram-se protegidos e sem danos aparentes": {"status": "OK", "observacao": ""},
        "Nao ha risco aparente de queda de componentes do evaporador": {"status": "NC", "observacao": "Parafuso de fixacao frouxo"},
        "Fluxo de ar encontra-se adequado e sem ruidos anormais": {"status": "OK", "observacao": ""}
    })

    resp_producao = json.dumps({
        "Piso limpo, sem agua, oleo ou residuos": {"status": "NC", "observacao": "Acumulo de oleo proximo a esteira 02"},
        "Iluminacao e ventilacao adequadas": {"status": "OK", "observacao": ""},
        "Equipamentos de movimentacao (paleteiras/empilhadeiras) em boas condicoes": {"status": "OK", "observacao": ""},
        "Protecoes de correias, polias e partes moveis de maquinas (NR 12)": {"status": "OK", "observacao": ""},
        "Quadros eletricos trancados e identificados (NR 10)": {"status": "OK", "observacao": ""},
        "Rotas de fuga e saidas de emergencia desobstruidas (NR 23)": {"status": "OK", "observacao": ""}
    })

    resp_estagiario = json.dumps({
        "Extintores dentro da validade e pressurizados": {"status": "OK", "observacao": ""},
        "Mangueiras de hidrante acopladas e sem vazamentos": {"status": "OK", "observacao": ""},
        "Iluminacao de emergencia testada e operacional": {"status": "NC", "observacao": "Luminaria de emergencia do bloco B sem bateria"},
        "Alarmes de incendio operacionais": {"status": "OK", "observacao": ""},
        "Chuveiros e lava-olhos de emergencia desobstruidos e limpos": {"status": "OK", "observacao": ""}
    })

    checklists = [
        ("CHECKLIST DE DESOSSA", "DESOSSA", "JOAO PEDRO TST", None, d1, resp_desossa),
        ("CHECKLIST DE EVAPORADORES", "EVAPORADORES", "MARIA SILVA TST", None, d2, resp_evaporador),
        ("CHECKLIST DE AREAS DE PRODUCAO", "AREAS DE PRODUCAO", "JOAO PEDRO TST", None, d3, resp_producao),
        ("EQUIPAMENTOS DE EMERGENCIA", "EMBALAGEM", "LUCAS ESTAGIARIO", "MARIA SILVA TST", d4, resp_estagiario)
    ]
    c.executemany('''INSERT INTO checklists 
                     (tipo_checklist, setor, responsavel, tst_validador, data_hora, respostas) 
                     VALUES (?, ?, ?, ?, ?, ?)''', checklists)

    # 5. ORDENS DE SERVICO
    dt_vencida = (hoje - timedelta(days=3)).strftime("%d/%m/%Y")
    dt_proxima = (hoje + timedelta(days=1)).strftime("%d/%m/%Y")
    dt_no_prazo = (hoje + timedelta(days=10)).strftime("%d/%m/%Y")

    abertura_1 = (hoje - timedelta(days=15)).strftime("%d/%m/%Y")
    abertura_2 = (hoje - timedelta(days=10)).strftime("%d/%m/%Y")
    abertura_3 = (hoje - timedelta(days=5)).strftime("%d/%m/%Y")
    abertura_4 = (hoje - timedelta(days=2)).strftime("%d/%m/%Y")

    hist_1 = json.dumps([f"{abertura_1} - JOAO PEDRO TST: OS Aberta via checklist.", f"{(hoje - timedelta(days=12)).strftime('%d/%m/%Y')} - CARLOS SUPERVISOR: Peca substituida e concluida."])
    hist_2 = json.dumps([f"{abertura_2} - MARIA SILVA TST: Solicitada manutencao corretiva na sustentacao do evaporador."])
    hist_3 = json.dumps([f"{abertura_3} - JOAO PEDRO TST: Identificado risco de escorregamento. Aguardando limpeza/manutencao."])
    hist_4 = json.dumps([f"{abertura_4} - LUCAS ESTAGIARIO: Validado por MARIA SILVA TST. Aguardando troca da luminaria."])

    ordens = [
        (1, "DESOSSA", "PROTECAO LATERAL DA SERRA FITA SOLTA", "JOAO PEDRO TST", "MARCOS ANTONIO", dt_vencida, "CONCLUIDA", abertura_1, hoje.strftime("%d/%m/%Y"), hist_1, "Servico finalizado e testado", None, None),
        (2, "EVAPORADORES", "HASTE DE SUSTENTACAO DO EVAPORADOR 03 COM CORROSAO EXCESSIVA E PARAFUSO FROUXO", "MARIA SILVA TST", "ROBERTO ALMEIDA", dt_vencida, "ABERTA", abertura_2, None, hist_2, "Urgencia alta - risco de queda", None, None),
        (3, "AREAS DE PRODUCAO", "ACUMULO DE OLEO PROXIMO A ESTEIRA 02 (RISCO DE ESCORREGAMENTO)", "JOAO PEDRO TST", "FERNANDA SOUZA", dt_proxima, "EM ANDAMENTO", abertura_3, None, hist_3, "Equipe de limpeza acionada", None, None),
        (4, "EMBALAGEM", "LUMINARIA DE EMERGENCIA DO BLOCO B SEM BATERIA/DANIFICADA", "LUCAS ESTAGIARIO", "EDSON SILVA", dt_no_prazo, "AGUARDANDO PECA", abertura_4, None, hist_4, "Solicitado pedido de compra da bateria", None, None)
    ]

    c.executemany('''INSERT INTO ordens_servico 
                     (checklist_id, setor, irregularidade, responsavel_solicitacao, gestor_responsavel, prazo_correcao, status, data_abertura, data_conclusao, historico, observacoes, foto_antes, foto_depois) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', ordens)

    # 6. METAS DE INSPEÇÃO
    mes_ano_atual = hoje.strftime("%m/%Y")
    metas = [
        ("JOAO PEDRO TST", "CHECKLIST DE DESOSSA", mes_ano_atual, 10),
        ("JOAO PEDRO TST", "CHECKLIST DE AREAS DE PRODUCAO", mes_ano_atual, 8),
        ("MARIA SILVA TST", "CHECKLIST DE EVAPORADORES", mes_ano_atual, 5),
        ("MARIA SILVA TST", "EQUIPAMENTOS DE EMERGENCIA", mes_ano_atual, 12)
    ]
    c.executemany("INSERT INTO metas (tst_nome, tipo_checklist, mes_ano, quantidade_prevista) VALUES (?, ?, ?, ?)", metas)

    conn.commit()
    conn.close()
    print("Banco de dados 'sesmt_control.db' alimentado com sucesso!")

if __name__ == "__main__":
    popular_banco_dados()