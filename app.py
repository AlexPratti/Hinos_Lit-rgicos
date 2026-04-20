import streamlit as st
import pdfplumber
import re
from supabase import create_client
import pandas as pd
import io

# Conexão original mantida
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])
BUCKET = "hinarios"

# Categorias específicas para o arquivo principal
CATEGORIAS_LITURGICOS = [
    "ORANTES", "INICIAIS E FINAIS", "PERDÃO", "GLÓRIA", "DEUS NOS FALA", 
    "SALMO", "ACLAMAÇÃO", "OFERTÓRIO", "LOUVOR", "SANTO", "CORDEIRO", 
    "PAZ", "COMUNHÃO", "BÍBLIA", "CRUZ", "LADAINHAS – SEQUÊNCIAS - PROCLAMAÇÕES", 
    "MARIA", "PRECES"
]

def process_pdf_adaptativo(file, nome_documento):
    data = []
    # Define a regra de categoria baseado no documento selecionado
    if "DIVERSOS" in nome_documento.upper():
        current_n1 = "HINOS DIVERSOS"
        categorias_permitidas = ["HINOS DIVERSOS"]
    else:
        current_n1 = "Sem Categoria"
        categorias_permitidas = CATEGORIAS_LITURGICOS

    with pdfplumber.open(file) as pdf:
        progresso = st.progress(0)
        total_paginas = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text: continue
            for line in text.split('\n'):
                t_limpo = line.strip()
                # Se o texto em maiúsculo for uma categoria permitida para este arquivo
                if t_limpo.upper() in categorias_permitidas:
                    current_n1 = t_limpo.upper()
                # Se for um hino numerado (Nível 2)
                elif re.match(r'^\d+\.', t_limpo):
                    data.append({"n1": current_n1, "n2": t_limpo, "pag": i + 1})
            progresso.progress((i + 1) / total_paginas)
    return data

def save_to_db(data):
    # Limpeza total para garantir que o banco reflita apenas o arquivo ativo
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    
    categorias_presentes = sorted(list(set([item['n1'] for item in data])))
    for cat_nome in categorias_presentes:
        res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_nome}).execute()
        if res.data:
            cat_id = res.data['id']
            itens = [
                {"categoria_id": cat_id, "nome_nivel2": item['n2'], "texto_completo": str(item['pag'])} 
                for item in data if item['n1'] == cat_nome
            ]
            if itens:
                supabase.table("hinos_conteudos").insert(itens).execute()
# --- INTERFACE ---
st.set_page_config(page_title="Hinário Visual", layout="wide")

st.subheader("📖 Seleção de Hinário")
# O usuário escolhe qual documento quer que o app exiba/atualize
doc_ativo = st.radio(
    "Qual arquivo deseja ativar no sistema?",
    ["HINOS LITÚRGICOS", "HINOS DIVERSOS"],
    horizontal=True
)

# Nomes dos arquivos em MAIÚSCULO para o Storage conforme solicitado
NOME_STORAGE = "HINOS LITÚRGICOS.pdf" if doc_ativo == "HINOS LITÚRGICOS" else "HINOS DIVERSOS.pdf"

# Tenta carregar o PDF persistente do Storage conforme a escolha do rádio
try:
    res_storage = supabase.storage.from_(BUCKET).download(NOME_STORAGE)
    arquivo_persistente = io.BytesIO(res_storage)
except:
    arquivo_persistente = None

with st.expander(f"⬆️ Upload para {doc_ativo}"):
    arquivo_novo = st.file_uploader("Selecione o arquivo PDF", type="pdf")
    if st.button(f"Atualizar Banco com {doc_ativo}") and arquivo_novo:
        with st.spinner("Sincronizando arquivo e banco..."):
            file_bytes = arquivo_novo.read()
            # Salva no Storage com o nome em maiúsculo (x-upsert para sobrescrever)
            supabase.storage.from_(BUCKET).upload(
                path=NOME_STORAGE, 
                file=file_bytes, 
                file_options={"x-upsert": "true"}
            )
            # Processa conforme a lógica do documento escolhido
            dados = process_pdf_adaptativo(io.BytesIO(file_bytes), doc_ativo)
            save_to_db(dados)
            st.success(f"{doc_ativo} sincronizado com sucesso!")
            st.rerun()

try:
    # Busca categorias (o banco conterá apenas as categorias do último arquivo sincronizado)
    res_cat = supabase.table("hinos_categorias").select("*").order("nome_nivel1").execute()
    if res_cat.data and arquivo_persistente:
        df_cat = pd.DataFrame(res_cat.data)
        
        c1, c2 = st.columns(2)
        with c1:
            escolha_n1 = st.selectbox("Categoria", df_cat['nome_nivel1'], key=f"cat_{doc_ativo}")
            id_n1 = int(df_cat[df_cat['nome_nivel1'] == escolha_n1]['id'].iloc)
        
        res_hinos = supabase.table("hinos_conteudos").select("*").eq("categoria_id", id_n1).execute().data
        
        if res_hinos:
            # Ordenação numérica fiel
            hinos_ord = sorted(res_hinos, key=lambda x: int(re.search(r'\d+', x['nome_nivel2']).group()))
            titulos = [h['nome_nivel2'] for h in hinos_ord]
            hino_sel = st.selectbox("Escolha o Hino:", titulos, key=f"h_{escolha_n1}_{doc_ativo}")
            
            dados_hino = next(h for h in res_hinos if h['nome_nivel2'] == hino_sel)
            p_num = int(dados_hino['texto_completo'])
            
            st.divider()
            with pdfplumber.open(arquivo_persistente) as pdf:
                page = pdf.pages[p_num - 1]
                text_lines = page.extract_text_lines()
                
                # Início exato na seleção do usuário
                y_ini = next((l['top'] for l in text_lines if hino_sel in l['text']), 0)
                
                # Fim no próximo título ou próxima categoria
                y_fim = page.height
                lista_bloqueio = CATEGORIAS_LITURGICOS + ["HINOS DIVERSOS"]
                for l in text_lines:
                    if l['top'] > y_ini + 5:
                        txt = l['text'].strip()
                        if re.match(r'^\d+\.', txt) or txt.upper() in lista_bloqueio:
                            y_fim = l['top']
                            break
                
                # Crop e Exibição visual
                img = page.crop((0, max(0, y_ini - 10), page.width, y_fim)).to_image(resolution=200).original
                st.image(img, use_container_width=True)
    else:
        st.info(f"O arquivo {doc_ativo} ainda não foi sincronizado ou está vazio.")
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
