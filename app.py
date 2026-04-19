import streamlit as st
from docx import Document
from supabase import create_client
import pandas as pd
import re

# Conexão
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])

def process_docx(file):
    doc = Document(file)
    data = []
    
    # 1. Identificação da Estrutura
    hinos_mapeados = []
    current_cat = "GERAL"
    
    # Regex flexível para o Sumário
    # Detecta: "1. Titulo .... 10" ou "TITULO .... 10"
    re_hino_sumario = re.compile(r'^(\d+[\.\)].+?)(?:\s\.+)?\s\d+$')
    re_secao_sumario = re.compile(r'^([A-ZÇÃÕÉÍÓÚ\s]{3,})(?:\s\.+)?\s\d+$')

    # Passo A: Ler Sumário
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        
        # Para se encontrar o início real dos hinos (evita ler o corpo como sumário)
        if text.startswith("ORANTES") and "...." not in text:
            break
            
        m_secao = re_secao_sumario.match(text)
        m_hino = re_hino_sumario.match(text)
        
        if m_secao:
            current_cat = m_secao.group(1).strip()
        elif m_hino:
            hinos_mapeados.append({"cat": current_cat, "titulo": m_hino.group(1).strip()})

    # Passo B: Capturar Letras (Busca os títulos no corpo do texto)
    titulos_alvo = {h['titulo']: "" for h in hinos_mapeados}
    hino_atual = None
    buffer = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text in titulos_alvo:
            if hino_atual:
                titulos_alvo[hino_atual] = "\n".join(buffer)
            hino_atual = text
            buffer = []
        elif hino_atual:
            buffer.append(text)
    
    if hino_atual:
        titulos_alvo[hino_atual] = "\n".join(buffer)

    # Passo C: Finalizar dados
    for h in hinos_mapeados:
        data.append({
            "n1": h['cat'],
            "n2": h['titulo'],
            "texto": titulos_alvo.get(h['titulo'], "Letra não encontrada.")
        })
    return data

def save_to_db(data):
    # Limpa dados anteriores
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    
    seen_cats = {}
    for item in data:
        cat_name = item['n1']
        if cat_name not in seen_cats:
            # Inserção de Categoria
            res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_name}).execute()
            if res.data:
                # O Supabase retorna uma lista, acessamos o primeiro elemento [0]
                seen_cats[cat_name] = res.data[0]['id']
        
        # Inserção de Conteúdo
        if cat_name in seen_cats:
            supabase.table("hinos_conteudos").insert({
                "categoria_id": seen_cats[cat_name],
                "nome_nivel2": item['n2'],
                "texto_completo": item['texto']
            }).execute()

# --- INTERFACE ---
st.set_page_config(page_title="Hinário Litúrgico", layout="wide")

with st.sidebar:
    st.title("⚙️ Painel Admin")
    arquivo = st.file_uploader("Upload .docx", type="docx")
    if st.button("🚀 Processar via Sumário") and arquivo:
        dados = process_docx(arquivo)
        if dados:
            save_to_db(dados)
            st.success(f"Sucesso! {len(dados)} hinos salvos.")
            st.rerun()
        else:
            st.error("Não foi possível extrair hinos do Sumário.")

# --- NAVEGAÇÃO ---
try:
    res_cat = supabase.table("hinos_categorias").select("*").order("id").execute()
    if res_cat.data:
        df_cat = pd.DataFrame(res_cat.data)
        c1, c2 = st.columns([1, 2])
        
        with c1:
            sel_n1 = st.selectbox("📌 Escolha a Seção:", df_cat['nome_nivel1'])
            id_n1 = int(df_cat[df_cat['nome_nivel1'] == sel_n1]['id'].iloc[0])
            
            busca = st.text_input("🔍 Busca:")
            hinos_db = supabase.table("hinos_conteudos").select("*").eq("categoria_id", id_n1).order("id").execute().data
            
            if hinos_db:
                if busca:
                    hinos_db = [h for h in hinos_db if busca.lower() in h['nome_nivel2'].lower()]
                
                lista = [h['nome_nivel2'] for h in hinos_db]
                if lista:
                    escolha = st.radio("📑 Selecione:", lista)
                    info = next(h for h in hinos_db if h['nome_nivel2'] == escolha)
                    with c2:
                        st.subheader(info['nome_nivel2'])
                        st.divider()
                        st.text(info['texto_completo'])
    else:
        st.info("💡 Banco de dados vazio. Faça o upload no menu lateral.")
except Exception as e:
    st.error(f"Erro: {e}")
