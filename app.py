import streamlit as st
import pdfplumber
import re
from supabase import create_client
import pandas as pd

# Conexão original mantida
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])

# Lista exata definida por você
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
def save_to_db(data):
    # Limpa dados antigos
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    
    for cat_nome in CATEGORIAS_ALVO:
        res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_nome}).execute()
        
        # Acesso seguro ao ID (Supabase retorna lista)
        if res.data:
            cat_id = res.data[0]['id']
            
            # Salvamos o intervalo de páginas no campo 'texto_completo' para não dar erro de coluna
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

with st.expander("⬆️ Sincronizar PDF"):
    arquivo = st.file_uploader("Selecione o PDF", type="pdf")
    if st.button("Atualizar Banco") and arquivo:
        dados = process_pdf_as_images(arquivo)
        save_to_db(dados)
        st.success("Sincronizado!")
        st.rerun()

try:
    res_cat = supabase.table("hinos_categorias").select("*").order("nome_nivel1").execute()
    if res_cat.data and arquivo:
        df_cat = pd.DataFrame(res_cat.data)
        c1, c2 = st.columns(2)
        with c1:
            escolha_n1 = st.selectbox("Categoria", df_cat['nome_nivel1'])
            id_n1 = int(df_cat[df_cat['nome_nivel1'] == escolha_n1]['id'])
        
        hinos = supabase.table("hinos_conteudos").select("*").eq("categoria_id", id_n1).execute().data

        if hinos:
            hino_sel = st.selectbox("Hino:", [h['nome_nivel2'] for h in hinos])
            dados_hino = next(h for h in hinos if h['nome_nivel2'] == hino_sel)
            
            # Recupera as páginas guardadas no campo de texto
            paginas = dados_hino['texto_completo'].split('-')
            p_ini, p_fim = int(paginas[0]), int(paginas[1])
            
            st.divider()
            with pdfplumber.open(arquivo) as pdf:
                for p_num in range(p_ini, p_fim + 1):
                    # Tira a "foto" da página para fidelidade total
                    img = pdf.pages[p_num - 1].to_image(resolution=200).original
                    st.image(img, use_container_width=True)
    else:
        st.info("Aguardando upload do PDF para visualização.")
except Exception as e:
    st.error(f"Erro de conexão ou dados: {e}")
