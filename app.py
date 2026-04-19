import streamlit as st
from docx import Document
from supabase import create_client
import pandas as pd
import re

# Conexão com Supabase
url = st.secrets["URL_SUPABASE"]
key = st.secrets["KEY_SUPABASE"]
supabase = create_client(url, key)

def process_docx(file):
    doc = Document(file)
    data = []
    
    # --- PASSO 1: MAPEAMENTO PELA ESTRUTURA DO SUMÁRIO ---
    current_cat = "GERAL"
    hinos_mapeados = []
    
    # Regex para detectar hinos no sumário (Ex: "1. VENHA A NÓS... 10")
    # Captura o título ignorando os pontos e o número da página no fim
    re_sumario = re.compile(r'^(.+?)(?:\s?\.+)\s?\d+$')

    paragraphs =

    for text in paragraphs:
        # Para de ler o sumário quando encontra o início real do conteúdo (página 10 no seu PDF)
        if text == "ORANTES" and "...." not in text:
            break
            
        if "...." in text:
            clean_text = re.sub(r'\.+\s*\d+$', '', text).strip()
            
            # Nível 1: CAIXA ALTA e sem número no início
            if clean_text.isupper() and not clean_text[0:1].isdigit():
                current_cat = clean_text
            # Nível 2: Começa com número
            elif clean_text[0:1].isdigit():
                hinos_mapeados.append({"n1": current_cat, "n2": clean_text})

    # --- PASSO 2: CAPTURA DO TEXTO NO CORPO DO DOCUMENTO ---
    conteudos = {h['n2']: [] for h in hinos_mapeados}
    hino_foco = None

    for text in paragraphs:
        # Se a linha for exatamente um título de hino mapeado
        if text in conteudos:
            hino_foco = text
        elif hino_foco:
            # Se encontrar uma nova Categoria (Caixa Alta), encerra a captura do hino atual
            if text.isupper() and len(text) < 50 and not text[0:1].isdigit() and text != hino_foco:
                hino_foco = None
            else:
                conteudos[hino_foco].append(text)

    # Passo 3: Consolidar dados
    for h in hinos_mapeados:
        data.append({
            "n1": h['n1'],
            "n2": h['n2'],
            "texto": "\n".join(conteudos[h['n2']])
        })
    return data

def save_to_db(data):
    # Limpa as tabelas existentes
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    
    seen_cats = {}
    for item in data:
        cat_name = item['n1']
        if cat_name not in seen_cats:
            res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_name}).execute()
            if res.data:
                seen_cats[cat_name] = res.data[0]['id']
        
        if cat_name in seen_cats:
            supabase.table("hinos_conteudos").insert({
                "categoria_id": seen_cats[cat_name],
                "nome_nivel2": item['n2'],
                "texto_completo": item['texto']
            }).execute()

# --- Interface ---
st.set_page_config(page_title="Hinos Litúrgicos", layout="wide")
st.title("📖 Hinário Litúrgico")

with st.expander("⬆️ Upload de novo arquivo (.docx)"):
    arquivo = st.file_uploader("Substituir hinário atual", type="docx")
    if st.button("Confirmar Processamento"):
        if arquivo:
            with st.spinner("Extraindo hinos conforme o sumário..."):
                dados = process_docx(arquivo)
                save_to_db(dados)
                st.success(f"Banco de dados atualizado! {len(dados)} hinos carregados.")
                st.rerun()

# Carregamento de Dados
try:
    res_cat = supabase.table("hinos_categorias").select("id, nome_nivel1").order("id").execute()
    
    if res_cat.data:
        df_cat = pd.DataFrame(res_cat.data)
        
        col_menu, col_texto = st.columns([1, 2])
        
        with col_menu:
            cat_selecionada = st.selectbox("1. Selecione a Categoria (Nível 1):", df_cat['nome_nivel1'])
            cat_id = int(df_cat[df_cat['nome_nivel1'] == cat_selecionada]['id'].iloc[0])
            
            busca = st.text_input("2. 🔍 Buscar hino:", placeholder="Digite nome ou número...")

            # Busca hinos da categoria
            query = supabase.table("hinos_conteudos").select("*").eq("categoria_id", cat_id).order("id")
            if busca:
                query = query.ilike("nome_nivel2", f"%{busca}%")
            
            res_hinos = query.execute()
            
            if res_hinos.data:
                hinos_lista = [h['nome_nivel2'] for h in res_hinos.data]
                escolha_hino = st.radio("Selecione para visualizar:", hinos_lista)
                hino_info = next(h for h in res_hinos.data if h['nome_nivel2'] == escolha_hino)
            else:
                st.warning("Nenhum hino encontrado.")
                hino_info = None

        with col_texto:
            if hino_info:
                st.subheader(hino_info['nome_nivel2'])
                st.divider()
                # st.text preserva a formatação original de versos e cifras
                st.text(hino_info['texto_completo'])
    else:
        st.info("O banco de dados está vazio. Por favor, suba um arquivo docx no menu lateral.")

except Exception as e:
    st.error(f"Erro ao conectar ao banco: {e}")
