import streamlit as st
import pdfplumber
import re
from supabase import create_client
import pandas as pd
import io

# Conexão original mantida
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])

# Configurações do Storage
BUCKET = "hinarios"
FILE_PATH = "hinario_atual.pdf"

CATEGORIAS_ALVO = [
    "ORANTES", "INICIAIS E FINAIS", "PERDÃO", "GLÓRIA", "DEUS NOS FALA", 
    "SALMO", "ACLAMAÇÃO", "OFERTÓRIO", "LOUVOR", "SANTO", "CORDEIRO", 
    "PAZ", "COMUNHÃO", "BÍBLIA", "CRUZ", "LADAINHAS – SEQUÊNCIAS - PROCLAMAÇÕES", 
    "MARIA", "PRECES"
]

def process_pdf_as_images(file):
    data = []
    current_n1 = "Sem Categoria"
    current_n2 = None
    start_page = 0
    
    with pdfplumber.open(file) as pdf:
        progresso = st.progress(0)
        total_paginas = len(pdf.pages)
        
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text: continue
            
            linhas = text.split('\n')
            for linha in linhas:
                texto_limpo = linha.strip()
                
                if texto_limpo.upper() in CATEGORIAS_ALVO:
                    current_n1 = texto_limpo.upper()
                    continue

                if re.match(r'^\d+\.', texto_limpo):
                    if current_n2:
                        # O hino anterior termina onde este começa
                        data.append({
                            "n1": current_n1, 
                            "n2": current_n2, 
                            "pag_inicio": start_page, 
                            "pag_fim": i + 1 
                        })
                    current_n2 = texto_limpo
                    start_page = i + 1
            
            progresso.progress((i + 1) / total_paginas)

        if current_n2:
            data.append({
                "n1": current_n1, "n2": current_n2, 
                "pag_inicio": start_page, "pag_fim": total_paginas
            })
    return data

def get_persistent_pdf():
    try:
        # Tenta baixar o arquivo do Storage
        res = supabase.storage.from_(BUCKET).download(FILE_PATH)
        return io.BytesIO(res)
    except:
        return None
def save_to_db(data):
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    
    for cat_nome in CATEGORIAS_ALVO:
        res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_nome}).execute()
        if res.data:
            cat_id = res.data[0]['id']
            itens = [
                {
                    "categoria_id": cat_id, 
                    "nome_nivel2": item['n2'], 
                    "texto_completo": f"{item['pag_inicio']}-{item['pag_fim']}" 
                } 
                for item in data if item['n1'] == cat_nome
            ]
            if itens:
                supabase.table("hinos_conteudos").insert(itens).execute()

# --- INTERFACE ---
st.set_page_config(page_title="Hinário Visual", layout="wide")

# Tenta carregar o PDF salvo anteriormente
arquivo_persistente = get_persistent_pdf()

with st.expander("⬆️ Upload PDF"):
    arquivo_novo = st.file_uploader("Selecione um novo arquivo para substituir o atual", type="pdf")
    if st.button("Atualizar Banco e Arquivo") and arquivo_novo:
        with st.spinner("Enviando para o Storage e processando..."):
            file_bytes = arquivo_novo.read()
            # Salva no Storage sobrescrevendo o anterior (x-upsert)
            supabase.storage.from_(BUCKET).upload(
                path=FILE_PATH,
                file=file_bytes,
                file_options={"x-upsert": "true"}
            )
            # Processa para o Banco de Dados
            dados = process_pdf_as_images(io.BytesIO(file_bytes))
            save_to_db(dados)
            st.success("Sincronizado e Salvo com Sucesso!")
            st.rerun()

# Usamos o arquivo que veio do Storage ou o que acabou de ser carregado
arquivo_para_uso = arquivo_persistente

try:
    res_cat = supabase.table("hinos_categorias").select("*").order("nome_nivel1").execute()
    if res_cat.data and arquivo_para_uso:
        df_cat = pd.DataFrame(res_cat.data)
        c1, c2 = st.columns(2)
        
        with c1:
            escolha_n1 = st.selectbox("Categoria", df_cat['nome_nivel1'], key="sel_cat")
            id_n1 = int(df_cat[df_cat['nome_nivel1'] == escolha_n1]['id'].iloc[0])
        
        # Filtro de hinos por categoria
        res_hinos = supabase.table("hinos_conteudos").select("*").eq("categoria_id", id_n1).execute().data
        
        if res_hinos:
            # Ordenação numérica dos hinos
            hinos_ord = sorted(res_hinos, key=lambda x: int(re.search(r'\d+', x['nome_nivel2']).group()))
            # Chave dinâmica para resetar a lista de hinos ao trocar de categoria
            hino_sel = st.selectbox("Hino:", [h['nome_nivel2'] for h in hinos_ord], key=f"h_{escolha_n1}")
            
            dados_hino = next(h for h in res_hinos if h['nome_nivel2'] == hino_sel)
            pag_str = dados_hino['texto_completo'].split('-')
            p_ini, p_fim = int(pag_str[0]), int(pag_str[1])
            
            st.divider()
            with pdfplumber.open(arquivo_para_uso) as pdf:
                # Se o hino começa e termina na mesma página (p_ini == p_fim), mostra só ela.
                # O range ajustado resolve parte do problema de mostrar hinos a mais.
                for p_num in range(p_ini, p_fim + 1):
                    img = pdf.pages[p_num - 1].to_image(resolution=200).original
                    st.image(img, use_container_width=True)
    else:
        if not arquivo_para_uso:
            st.info("Nenhum hinário salvo. Por favor, faça o primeiro upload acima.")
        else:
            st.info("Carregando banco de dados...")
except Exception as e:
    st.error(f"Aguardando dados... (Erro: {e})")
