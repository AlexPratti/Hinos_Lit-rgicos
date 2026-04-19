import streamlit as st
from docx import Document
from supabase import create_client
import pandas as pd

# Conexão
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])

def process_docx(file):
    doc = Document(file)
    data = []
    current_n1 = "Sem Categoria"
    current_n2 = None
    current_text = []

    for para in doc.paragraphs:
        style = para.style.name
        texto = para.text.strip()
        
        if not texto: continue

        # Identifica Nível 1 (Heading 1 ou Título 1)
        if 'Heading 1' in style or 'Título 1' in style:
            current_n1 = texto
            current_n2 = None 
            
        # Identifica Nível 2 (Heading 2 ou Título 2)
        elif 'Heading 2' in style or 'Título 2' in style:
            # Salva o anterior antes de começar um novo
            if current_n2:
                data.append({"n1": current_n1, "n2": current_n2, "texto": "\n".join(current_text)})
            
            current_n2 = texto
            current_text = [] # Limpa para o novo hino
            
        # Captura o texto normal (Corpo do texto)
        else:
            if current_n2:
                current_text.append(texto)

    # Salva o último hino do arquivo
    if current_n2:
        data.append({"n1": current_n1, "n2": current_n2, "texto": "\n".join(current_text)})
        
    return data

def save_to_db(data):
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    
    categorias_unicas = sorted(list(set([item['n1'] for item in data])))
    for cat_nome in categorias_unicas:
        res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_nome}).execute()
        cat_id = res.data[0]['id']
        
        itens = [
            {"categoria_id": cat_id, "nome_nivel2": item['n2'], "texto_completo": item['texto']} 
            for item in data if item['n1'] == cat_nome
        ]
        if itens:
            supabase.table("hinos_conteudos").insert(itens).execute()

# --- INTERFACE ---
st.set_page_config(page_title="Hinário", layout="wide")

with st.expander("⬆️ Configurações de Upload"):
    arquivo = st.file_uploader("Upload .docx", type="docx")
    if st.button("Atualizar Banco de Dados") and arquivo:
        dados = process_docx(arquivo)
        save_to_db(dados)
        st.success(f"Processado: {len(dados)} hinos encontrados.")
        st.rerun()

# --- EXIBIÇÃO ---
try:
    res_cat = supabase.table("hinos_categorias").select("*").order("nome_nivel1").execute()
    if res_cat.data:
        df_cat = pd.DataFrame(res_cat.data)
        
        c1, c2 = st.columns(2)
        with c1:
            escolha_n1 = st.selectbox("Selecione a Categoria", df_cat['nome_nivel1'])
            id_n1 = int(df_cat[df_cat['nome_nivel1'] == escolha_n1]['id'].iloc[0])
        
        with c2:
            termo = st.text_input("🔍 Buscar hino por nome")

        # Filtra hinos
        query = supabase.table("hinos_conteudos").select("*").eq("categoria_id", id_n1)
        if termo:
            query = query.ilike("nome_nivel2", f"%{termo}%")
        
        hinos = query.execute().data

        if hinos:
            # Lista de títulos para o Radio
            titulos_hinos = [h['nome_nivel2'] for h in hinos]
            hino_selecionado_nome = st.radio("Escolha o hino para ler:", titulos_hinos)
            
            # Mostra o conteúdo do hino selecionado
            conteudo_hino = next(h for h in hinos if h['nome_nivel2'] == hino_selecionado_nome)
            
            st.markdown("---")
            st.subheader(conteudo_hino['nome_nivel2'])
            st.markdown(f"```\n{conteudo_hino['texto_completo']}\n```") # Mantém a formatação de versos
        else:
            st.warning("Nenhum hino encontrado nesta categoria/busca.")
except Exception as e:
    st.info("Aguardando upload do primeiro arquivo...")
