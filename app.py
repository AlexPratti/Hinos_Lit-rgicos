import streamlit as st
from docx import Document
from supabase import create_client
import pandas as pd
import re

# Conexão
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])

def is_paragraph_bold(para):
    """Verifica se o parágrafo inteiro está em negrito."""
    if para.style.name.startswith('Heading') or para.style.name.startswith('Título'):
        return True
    # Verifica se todos os 'runs' (trechos de texto) do parágrafo são negrito
    if para.runs:
        return all(run.bold for run in para.runs if run.text.strip())
    return False

def process_docx(file):
    doc = Document(file)
    data = []
    current_n1 = "OUTROS"
    current_n2 = None
    current_text = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text or "...." in text: continue

        # IDENTIFICAÇÃO DE HINOS (Nível 2) - Padrão "1. " ou "12. "
        if re.match(r'^\d+\.\s', text):
            if current_n2:
                data.append({"n1": current_n1, "n2": current_n2, "texto": "\n".join(current_text)})
            current_n2 = text
            current_text = []
            continue

        # IDENTIFICAÇÃO DE SEÇÕES (Nível 1) - Todo Maiúsculo + Negrito + Sem Números
        if text.isupper() and is_paragraph_bold(para) and not text[0:1].isdigit():
            current_n1 = text
            continue

        # CORPO DO TEXTO
        if current_n2:
            current_text.append(text)

    if current_n2:
        data.append({"n1": current_n1, "n2": current_n2, "texto": "\n".join(current_text)})
    return data

def save_to_db(data):
    # Limpeza total
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    
    # Inserção mantendo a ordem do arquivo
    seen_cats = {}
    for item in data:
        cat_name = item['n1']
        if cat_name not in seen_cats:
            res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_name}).execute()
            seen_cats[cat_name] = res.data['id']
        
        supabase.table("hinos_conteudos").insert({
            "categoria_id": seen_cats[cat_name],
            "nome_nivel2": item['n2'],
            "texto_completo": item['texto']
        }).execute()

# --- INTERFACE ---
st.set_page_config(page_title=" Hinário", layout="wide")

with st.sidebar:
    st.title("⚙️ Admin")
    arquivo = st.file_uploader("Arquivo Hinário (.docx)", type="docx")
    if st.button("🚀 Limpar e Atualizar Banco"):
        if arquivo:
            with st.spinner("Processando..."):
                dados = process_docx(arquivo)
                save_to_db(dados)
                st.success(f"Carregado: {len(dados)} hinos!")
                st.rerun()

# --- NAVEGAÇÃO ---
try:
    # Carrega categorias para o selectbox
    res_cat = supabase.table("hinos_categorias").select("*").order("id").execute()
    if res_cat.data:
        df_cat = pd.DataFrame(res_cat.data)
        
        col_nav, col_txt = st.columns([1, 2])
        
        with col_nav:
            cat_sel = st.selectbox("1. Escolha a Seção (Nível 1):", df_cat['nome_nivel1'])
            cat_id = int(df_cat[df_cat['nome_nivel1'] == cat_sel]['id'].iloc)
            
            busca = st.text_input("🔍 Busca por palavra:")
            
            # Busca hinos da categoria selecionada
            q_hinos = supabase.table("hinos_conteudos").select("*").eq("categoria_id", cat_id).order("id")
            if busca:
                q_hinos = q_hinos.ilike("nome_nivel2", f"%{busca}%")
            
            hinos_data = q_hinos.execute().data
            
            if hinos_data:
                hino_escolhido = st.radio("2. Selecione o hino:", [h['nome_nivel2'] for h in hinos_data])
                txt_hino = next(h for h in hinos_data if h['nome_nivel2'] == hino_escolhido)
            else:
                st.warning("Nenhum hino nesta busca.")
                txt_hino = None

        with col_txt:
            if txt_hino:
                st.subheader(txt_hino['nome_nivel2'])
                st.divider()
                st.text(txt_hino['texto_completo']) # Text preserva a formatação original
    else:
        st.info("Banco vazio. Suba o arquivo no menu lateral.")
except Exception as e:
    st.error(f"Erro: {e}")
