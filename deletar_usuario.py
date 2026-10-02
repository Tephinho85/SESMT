# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd

# Conecta ao banco de dados do SESMT
conn = sqlite3.connect("sesmt_control.db")

print("--- USUÁRIOS CADASTRADOS ---")
df_users = pd.read_sql_query("SELECT id, nome FROM usuarios", conn)
print(df_users)

print("\n--- ORDENS DE SERVIÇO ABERTAS ---")
df_os = pd.read_sql_query("SELECT id, setor, status, data_abertura FROM ordens_servico", conn)
print(df_os)

conn.close()