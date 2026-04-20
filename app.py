import streamlit as st
import pdfplumber
import re
from supabase import create_client
import pandas as pd
import io

supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])
BUCKET = "hinarios"

CATEGORIAS_LITURGICOS = ["ORANTES", "INICIAIS E FINAIS", "PERDÃO", "GLÓRIA", "DEUS NOS FALA", "SALMO", "ACLAMAÇÃO", "OFERTÓRIO", "LOUVOR", "SANTO", "CORDEIRO", "PAZ", "COMUNHÃO", "BÍBLIA", "CRUZ", "LADAINHAS – SEQUÊNCIAS - PROCLAMAÇÕES", "MARIA", "PRECES"]

def process_pdf_original(file, categoria_fixa=None):
    data = []
    current_n1 = categoria_fixa if categoria_fixa else "Sem Categoria"
    with pdfplumber.open(file) as pdf:
        progresso = st.progress(0)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text: continue
            for line in text.split('\n'):
                t_limpo = line.strip()
                if not t_limpo or "...." in t_limpo: continue
                if not categoria_fixa and t_limpo.upper() in CATEGORIAS_LITURGICOS:
                    current_n1 = t_limpo.upper()
                elif re.match(r'^\d+\.', t_limpo):
                    data.append({"n1": current_n1, "n2": t_limpo, "pag": i + 1})
            progresso.progress((i + 1) / len(pdf.pages))
    return data

def save_to_db(data, origem):
    # Deleta apenas os dados da aba correspondente
    supabase.table("hinos_conteudos").delete().eq("origem", origem).execute()
    supabase.table("hinos_categorias").delete().eq("origem", origem).execute()
    
    categorias_presentes = sorted(list(set([item['n1'] for item in data])))
    for cat_nome in categorias_presentes:
        res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_nome, "origem": origem}).execute()
        if res.data:
            cat_id = res.data[0]['id']
            itens = [{"categoria_id": cat_id, "nome_nivel2": item['n2'], "texto_completo": str(item['pag']), "origem": origem} for item in data if item['n1'] == cat_nome]
            if itens:
                supabase.table("hinos_conteudos").insert(itens).execute()
st.set_page_config(page_title="Hinário Litúrgico", layout="wide")
tab1, tab2 = st.tabs(["📖 HINOS LITÚRGICOS", "🎸 HINOS DIVERSOS"])

# --- ABA 1: HINOS LITÚRGICOS ---
with tab1:
    NOME_STORAGE_LIT = "HINOS_LITURGICOS.pdf"
    try:
        pdf_lit = io.BytesIO(supabase.storage.from_(BUCKET).download(NOME_STORAGE_LIT))
    except: pdf_lit = None

    with st.expander("⬆️ Sincronizar Hinos Litúrgicos"):
        up1 = st.file_uploader("PDF Litúrgico", type="pdf", key="u1")
        if st.button("Sincronizar Litúrgicos", key="b1"):
            bytes_pdf = up1.read()
            supabase.storage.from_(BUCKET).upload(path=NOME_STORAGE_LIT, file=bytes_pdf, file_options={"x-upsert": "true"})
            save_to_db(process_pdf_original(io.BytesIO(bytes_pdf)), "LITURGICO")
            st.rerun()

    if pdf_lit:
        res_cat = supabase.table("hinos_categorias").select("*").eq("origem", "LITURGICO").order("nome_nivel1").execute()
        if res_cat.data:
            df = pd.DataFrame(res_cat.data)
            c1, c2 = st.columns(2)
            with c1:
                sel_cat = st.selectbox("Categoria", df['nome_nivel1'], key="c1")
                id_cat = int(df[df['nome_nivel1'] == sel_cat]['id'].iloc[0])
            hinos = supabase.table("hinos_conteudos").select("*").eq("categoria_id", id_cat).execute().data
            if hinos:
                h_ord = sorted(hinos, key=lambda x: int(re.search(r'\d+', x['nome_nivel2']).group()))
                hino_sel = st.selectbox("Hino", [h['nome_nivel2'] for h in h_ord], key="h1")
                item = next(h for h in hinos if h['nome_nivel2'] == hino_sel)
                p_num = int(item['texto_completo'])
                with pdfplumber.open(pdf_lit) as pdf:
                    page = pdf.pages[p_num - 1]
                    lines = page.extract_text_lines()
                    y_ini = next((l['top'] for l in lines if hino_sel in l['text']), 0)
                    y_fim = page.height
                    for l in lines:
                        if l['top'] > y_ini + 5 and (re.match(r'^\d+\.', l['text'].strip()) or l['text'].strip().upper() in CATEGORIAS_LITURGICOS):
                            y_fim = l['top']; break
                    img = page.crop((0, max(0, y_ini-10), page.width, y_fim)).to_image(resolution=200).original
                    st.image(img, use_container_width=True)
                    st.markdown("<style>img { cursor: zoom-in; }</style>", unsafe_allow_html=True)

# --- ABA 2: HINOS DIVERSOS ---
with tab2:
    NOME_STORAGE_DIV = "HINOS_DIVERSOS.pdf"
    try:
        pdf_div = io.BytesIO(supabase.storage.from_(BUCKET).download(NOME_STORAGE_DIV))
    except: pdf_div = None

    with st.expander("⬆️ Sincronizar Hinos Diversos"):
        up2 = st.file_uploader("PDF Diversos", type="pdf", key="u2")
        if st.button("Sincronizar Diversos", key="b2"):
            bytes_pdf = up2.read()
            supabase.storage.from_(BUCKET).upload(path=NOME_STORAGE_DIV, file=bytes_pdf, file_options={"x-upsert": "true"})
            save_to_db(process_pdf_original(io.BytesIO(bytes_pdf), "HINOS DIVERSOS"), "DIVERSOS")
            st.rerun()

    if pdf_div:
        res_cat = supabase.table("hinos_categorias").select("*").eq("origem", "DIVERSOS").execute()
        if res_cat.data:
            id_cat = res_cat.data[0]['id']
            hinos = supabase.table("hinos_conteudos").select("*").eq("categoria_id", id_cat).execute().data
            if hinos:
                h_ord = sorted(hinos, key=lambda x: int(re.search(r'\d+', x['nome_nivel2']).group()))
                hino_sel = st.selectbox("Hino", [h['nome_nivel2'] for h in h_ord], key="h2")
                item = next(h for h in hinos if h['nome_nivel2'] == hino_sel)
                p_num = int(item['texto_completo'])
                with pdfplumber.open(pdf_div) as pdf:
                    page = pdf.pages[p_num - 1]
                    lines = page.extract_text_lines()
                    y_ini = next((l['top'] for l in lines if hino_sel in l['text']), 0)
                    y_fim = page.height
                    for l in lines:
                        if l['top'] > y_ini + 5 and re.match(r'^\d+\.', l['text'].strip()):
                            y_fim = l['top']; break
                    st.image(page.crop((0, max(0, y_ini-10), page.width, y_fim)).to_image(resolution=200).original, use_container_width=True)
                    st.markdown("<style>img { cursor: zoom-in; }</style>", unsafe_allow_html=True)
