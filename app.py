import streamlit as st
import pdfplumber
import re
from supabase import create_client
import pandas as pd
import io

# Conexão original mantida
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])
BUCKET, FILE_PATH = "hinarios", "hinario_atual.pdf"

CATEGORIAS_ALVO = ["ORANTES", "INICIAIS E FINAIS", "PERDÃO", "GLÓRIA", "DEUS NOS FALA", "SALMO", "ACLAMAÇÃO", "OFERTÓRIO", "LOUVOR", "SANTO", "CORDEIRO", "PAZ", "COMUNHÃO", "BÍBLIA", "CRUZ", "LADAINHAS – SEQUÊNCIAS - PROCLAMAÇÕES", "MARIA", "PRECES"]

def process_pdf_simple(file):
    data = []
    current_n1 = "Sem Categoria"
    with pdfplumber.open(file) as pdf:
        progresso = st.progress(0)
        total_pags = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text: continue
            for line in text.split('\n'):
                t_limpo = line.strip()
                if t_limpo.upper() in CATEGORIAS_ALVO:
                    current_n1 = t_limpo.upper()
                elif re.match(r'^\d+\.', t_limpo):
                    data.append({"n1": current_n1, "n2": t_limpo, "pag": i + 1})
            progresso.progress((i + 1) / total_pags)
    return data

def save_to_db(data):
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    for cat in CATEGORIAS_ALVO:
        res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat}).execute()
        if res.data:
            cat_id = res.data[0]['id']
            # Salvamos apenas a página no texto_completo para simplificar a busca do crop
            itens = [{"categoria_id": cat_id, "nome_nivel2": item['n2'], "texto_completo": str(item['pag'])} for item in data if item['n1'] == cat]
            if itens: supabase.table("hinos_conteudos").insert(itens).execute()
# --- INTERFACE ---
st.set_page_config(page_title="Hinário Visual", layout="wide")

try:
    pdf_res = supabase.storage.from_(BUCKET).download(FILE_PATH)
    arquivo_persistente = io.BytesIO(pdf_res)
except: arquivo_persistente = None

with st.expander("⬆️ Upload PDF"):
    novo = st.file_uploader("Selecione o arquivo", type="pdf")
    if st.button("Atualizar Banco") and novo:
        bytes_pdf = novo.read()
        supabase.storage.from_(BUCKET).upload(path=FILE_PATH, file=bytes_pdf, file_options={"x-upsert": "true"})
        dados = process_pdf_simple(io.BytesIO(bytes_pdf))
        save_to_db(dados)
        st.success("Sincronizado!")
        st.rerun()

try:
    res_cat = supabase.table("hinos_categorias").select("*").order("nome_nivel1").execute()
    if res_cat.data and arquivo_persistente:
        df_cat = pd.DataFrame(res_cat.data)
        c1, c2 = st.columns(2)
        with c1:
            escolha_n1 = st.selectbox("Categoria", df_cat['nome_nivel1'], key="cat")
            id_n1 = int(df_cat[df_cat['nome_nivel1'] == escolha_n1]['id'].iloc[0])
        
        hinos = supabase.table("hinos_conteudos").select("*").eq("categoria_id", id_n1).execute().data
        if hinos:
            # Sua ordenação numérica original
            hinos_ord = sorted(hinos, key=lambda x: int(re.search(r'\d+', x['nome_nivel2']).group()))
            titulos_lista = [h['nome_nivel2'] for h in hinos_ord]
            hino_sel = st.selectbox("Hino", titulos_lista, key=f"h_{escolha_n1}")
            
            # DETERMINAÇÃO DO INÍCIO E FIM PARA O CROP
            idx_atual = titulos_lista.index(hino_sel)
            proximo_titulo = titulos_lista[idx_atual + 1] if idx_atual + 1 < len(titulos_lista) else None

            item_db = next(h for h in hinos if h['nome_nivel2'] == hino_sel)
            p_num = int(item_db['texto_completo'])

            st.divider()
            with pdfplumber.open(arquivo_persistente) as pdf:
                page = pdf.pages[p_num - 1]
                words = page.extract_words()

                # 1. Busca o Início (y_ini): baseado exatamente no hino selecionado
                num_selecionado = hino_sel.split()[0] # ex: "2."
                y_ini = next((w['top'] for w in words if w == num_selecionado), 0)

                # 2. Busca o Fim (y_fim): baseado no próximo hino da lista
                y_fim = page.height
                if proximo_titulo:
                    num_proximo = proximo_titulo.split()[0] # ex: "3."
                    # Só corta na mesma página se o próximo hino estiver nela
                    y_fim = next((w['top'] for w in words if w == num_proximo), page.height)
                
                # 3. Executa o Recorte
                if y_fim <= y_ini: y_fim = page.height
                img = page.crop((0, y_ini - 10, page.width, y_fim - 5)).to_image(resolution=200).original
                st.image(img, use_container_width=True)
    else:
        st.info("Aguardando PDF...")
except Exception as e:
    st.error(f"Erro: {e}")
