import streamlit as st
from docx import Document
from supabase import create_client
import pandas as pd
import re

# Conexão segura
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])

def process_docx(file):
    doc = Document(file)
    data = []
    current_cat = "GERAL"
    current_hino = None
    current_text = []

    # Regex para hinos: número seguido de ponto e espaço (Ex: "1. ")
    re_hino = re.compile(r'^\d+[\.\)]\s+')

    for para in doc.paragraphs:
        text = para.text.strip()
        
        # Ignora linhas vazias ou do sumário
        if not text or "...." in text:
            continue

        # 1. IDENTIFICA HINO (Nível 2)
        if re_hino.match(text):
            if current_hino:
                data.append({"n1": current_cat, "n2": current_hino, "texto": "\n".join(current_text)})
            current_hino = text
            current_text = []
            continue

        # 2. IDENTIFICA SEÇÃO (Nível 1)
        # Se for MAIÚSCULO, curto e não for hino
        if text.isupper() and len(text) < 50 and not text[0:1].isdigit():
            current_cat = text
            continue

        # 3. CAPTURA O TEXTO DA LETRA
        if current_hino:
            current_text.append(text)

    # Adiciona o último hino
    if current_hino:
        data.append({"n1": current_cat, "n2": current_hino, "texto": "\n".join(current_text)})
    
    return data

def save_to_db(data):
    # Limpa dados antigos
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    
    seen_cats = {}
    for item in data:
        cat_name = item['n1']
        if cat_name not in seen_cats:
            res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_name}).execute()
            if res.data:
                # Pega o ID do dicionário dentro da lista
                seen_cats[cat_name] = res.data[0]['id']
        
        if cat_name in seen_cats:
            supabase.table("hinos_conteudos").insert({
                "categoria_id": seen_cats[cat_name],
                "nome_nivel2": item['n2'],
                "texto_completo": item['texto']
            }).execute()

# --- INTERFACE ---
st.set_page_config(page_title="Hinário", layout="wide")

with st.sidebar:
    st.title("⚙️ Admin")
    arquivo = st.file_uploader("Arquivo .docx", type="docx")
    if st.button("🚀 Processar Hinário") and arquivo:
        with st.spinner("Lendo hinos..."):
            dados = process_docx(arquivo)
            save_to_db(dados)
            st.success(f"Carregados {len(dados)} hinos!")
            st.rerun()

# --- EXIBIÇÃO ---
try:
    res_cat = supabase.table("hinos_categorias").select("*").order("id").execute()
    if res_cat.data:
        df_cat = pd.DataFrame(res_cat.data)
        col1, col2 = st.columns([1, 2])
        
        with col1:
            escolha_n1 = st.selectbox("📌 Seção:", df_cat['nome_nivel1'])
            cat_id = int(df_cat[df_cat['nome_nivel1'] == escolha_n1]['id'].iloc[0])
            
            busca = st.text_input("🔍 Busca por nome:")
            
            res_h = supabase.table("hinos_conteudos").select("*").eq("categoria_id", cat_id).order("id").execute().data
            if res_h:
                if busca:
                    res_h = [h for h in res_h if busca.lower() in h['nome_nivel2'].lower()]
                
                nomes_hinos = [h['nome_nivel2'] for h in res_h]
                if nomes_hinos:
                    hino_sel_nome = st.radio("📑 Escolha o hino:", nomes_hinos)
                    hino_final = next(h for h in res_h if h['nome_nivel2'] == hino_sel_nome)
                    
                    with col2:
                        st.subheader(hino_final['nome_nivel2'])
                        st.divider()
                        st.text(hino_final['texto_completo'])
    else:
        st.info("Banco vazio. Suba o arquivo no menu lateral.")
except Exception as e:
    st.error(f"Erro: {e}")
