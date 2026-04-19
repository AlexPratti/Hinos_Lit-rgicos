import streamlit as st
from docx import Document
from supabase import create_client
import pandas as pd
import re

# Conexão
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])

def process_docx(file):
    doc = Document(file)
    paragraphs =
    
    data = []
    hinos_mapeados = []
    current_cat = "GERAL"
    
    # --- PASSO 1: LER APENAS O SUMÁRIO ---
    # O sumário termina quando encontramos a primeira seção real ou o primeiro hino sem pontinhos
    for text in paragraphs:
        # Se a linha tem muitos pontos, é sumário
        if "...." in text:
            # Limpa o texto removendo os pontos e o número da página no final
            clean_text = re.sub(r'\.+\s*\d+$', '', text).strip()
            
            # Se começar com número, é Nível 2 (Hino)
            if clean_text[0:1].isdigit():
                hinos_mapeados.append({"cat": current_cat, "titulo": clean_text})
            # Se for caixa alta e não começar com número, é Nível 1 (Categoria)
            elif clean_text.isupper():
                current_cat = clean_text
        
        # Se encontrarmos o início do conteúdo real, paramos de ler o sumário
        if text == "ORANTES" and "...." not in text:
            break

    # --- PASSO 2: BUSCAR CONTEÚDO NO CORPO DO TEXTO ---
    titulos_alvo = {h['titulo']: "" for h in hinos_mapeados}
    hino_atual = None
    buffer = []

    for text in paragraphs:
        if text in titulos_alvo:
            if hino_atual:
                titulos_alvo[hino_atual] = "\n".join(buffer)
            hino_atual = text
            buffer = []
        elif hino_atual:
            # Evita capturar outros títulos de hinos como corpo de texto
            if not any(t == text for t in titulos_alvo):
                buffer.append(text)
    
    if hino_atual:
        titulos_alvo[hino_atual] = "\n".join(buffer)

    # --- PASSO 3: ORGANIZAR DADOS FINAIS ---
    for h in hinos_mapeados:
        data.append({
            "n1": h['cat'],
            "n2": h['titulo'],
            "texto": titulos_alvo.get(h['titulo'], "Letra não encontrada.")
        })
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
                seen_cats[cat_name] = res.data[0]['id'] # Acessa o ID do primeiro item da lista
        
        if cat_name in seen_cats:
            supabase.table("hinos_conteudos").insert({
                "categoria_id": seen_cats[cat_name],
                "nome_nivel2": item['n2'],
                "texto_completo": item['texto']
            }).execute()

# --- INTERFACE ---
st.set_page_config(page_title="Hinário Litúrgico", layout="wide")

with st.sidebar:
    st.title("⚙️ Administração")
    arquivo = st.file_uploader("Upload do Hinário (.docx)", type="docx")
    if st.button("🚀 Processar via Sumário"):
        if arquivo:
            with st.spinner("Extraindo do sumário..."):
                dados = process_docx(arquivo)
                if dados:
                    save_to_db(dados)
                    st.success(f"Sucesso! {len(dados)} hinos carregados.")
                    st.rerun()
                else:
                    st.error("O padrão do sumário não foi reconhecido.")

# --- EXIBIÇÃO ---
try:
    res_cat = supabase.table("hinos_categorias").select("*").order("id").execute()
    if res_cat.data:
        df_cat = pd.DataFrame(res_cat.data)
        col1, col2 = st.columns([1, 2])
        
        with col1:
            sel_n1 = st.selectbox("📌 Selecione a Seção:", df_cat['nome_nivel1'])
            cat_id = int(df_cat[df_cat['nome_nivel1'] == sel_n1]['id'].iloc[0])
            
            busca = st.text_input("🔍 Busca rápida:")
            
            hinos_db = supabase.table("hinos_conteudos").select("*").eq("categoria_id", cat_id).order("id").execute().data
            if hinos_db:
                if busca:
                    hinos_db = [h for h in hinos_db if busca.lower() in h['nome_nivel2'].lower()]
                
                lista = [h['nome_nivel2'] for h in hinos_db]
                if lista:
                    escolha = st.radio("📑 Selecione o hino:", lista)
                    info = next(h for h in hinos_db if h['nome_nivel2'] == escolha)
                    with col2:
                        st.subheader(info['nome_nivel2'])
                        st.divider()
                        st.text(info['texto_completo'])
    else:
        st.info("💡 Banco vazio. Faça o upload no menu lateral.")
except Exception as e:
    st.error(f"Aguardando configuração ou upload: {e}")
