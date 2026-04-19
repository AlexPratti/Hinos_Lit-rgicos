import streamlit as st
import pdfplumber
import re
from supabase import create_client
import pandas as pd

# Conexão
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])

CATEGORIAS_ALVO = [
    "ORANTES", "INICIAIS E FINAIS", "PERDÃO", "GLÓRIA", "DEUS NOS FALA", 
    "SALMO", "ACLAMAÇÃO", "OFERTÓRIO", "LOUVOR", "SANTO", "CORDEIRO", 
    "PAZ", "COMUNHÃO", "BÍBLIA", "CRUZ", "LADAINHAS – SEQUÊNCIAS - PROCLAMAÇÕES", 
    "MARIA", "PRECES"
]

def process_pdf_with_coords(file):
    data = []
    current_n1 = "Sem Categoria"
    current_n2 = None
    
    with pdfplumber.open(file) as pdf:
        progresso = st.progress(0)
        for i, page in enumerate(pdf.pages):
            # Extraímos as palavras com coordenadas para saber onde o hino começa
            words = page.extract_words()
            
            # Agrupamos palavras em linhas para identificar títulos
            linhas_texto = page.extract_text().split('\n')
            
            for texto_linha in linhas_texto:
                texto_limpo = texto_linha.strip()
                
                if texto_limpo.upper() in CATEGORIAS_ALVO:
                    current_n1 = texto_limpo.upper()
                    continue

                if re.match(r'^\d+\.', texto_limpo):
                    # Localiza a coordenada Y do título na página
                    matching_words = in texto_limpo]
                    y_top = matching_words[0]['top'] if matching_words else 0
                    
                    # Se já havia um hino anterior, o 'y_bottom' dele é o 'y_top' deste
                    if data and data[-1]['n2'] and data[-1]['pag_fim'] == i + 1:
                        data[-1]['y_fim'] = y_top - 5 # Pequena margem de segurança

                    data.append({
                        "n1": current_n1,
                        "n2": texto_limpo,
                        "pag_inicio": i + 1,
                        "y_ini": y_top - 10,
                        "pag_fim": i + 1,
                        "y_fim": page.height # Inicialmente vai até o fim da página
                    })
            progresso.progress((i + 1) / len(pdf.pages))
    return data
def save_to_db(data):
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    
    for cat_nome in CATEGORIAS_ALVO:
        res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_nome}).execute()
        if res.data:
            cat_id = res.data['id']
            # Salvamos as coordenadas como string no texto_completo: "pag_ini;y_ini;pag_fim;y_fim"
            itens = [
                {
                    "categoria_id": cat_id, "nome_nivel2": item['n2'],
                    "texto_completo": f"{item['pag_inicio']};{item['y_ini']};{item['pag_fim']};{item['y_fim']}"
                } for item in data if item['n1'] == cat_nome
            ]
            if itens: supabase.table("hinos_conteudos").insert(itens).execute()

# --- INTERFACE ---
st.set_page_config(page_title="Hinário Crop", layout="wide")
arquivo = st.file_uploader("Upload PDF", type="pdf")

if st.button("Atualizar Banco") and arquivo:
    dados = process_pdf_with_coords(arquivo)
    save_to_db(dados)
    st.success("Sincronizado!")

try:
    res_cat = supabase.table("hinos_categorias").select("*").order("nome_nivel1").execute()
    if res_cat.data and arquivo:
        df_cat = pd.DataFrame(res_cat.data)
        escolha_n1 = st.selectbox("Categoria", df_cat['nome_nivel1'], key="c1")
        id_n1 = int(df_cat[df_cat['nome_nivel1'] == escolha_n1]['id'].iloc)
        
        hinos = supabase.table("hinos_conteudos").select("*").eq("categoria_id", id_n1).execute().data
        if hinos:
            # Ordenação numérica correta
            hinos = sorted(hinos, key=lambda x: int(re.search(r'\d+', x['nome_nivel2']).group()))
            hino_sel = st.selectbox("Hino:", [h['nome_nivel2'] for h in hinos], key=f"h_{escolha_n1}")
            
            item = next(h for h in hinos if h['nome_nivel2'] == hino_sel)
            p_ini, y_ini, p_fim, y_fim = map(float, item['texto_completo'].split(';'))

            with pdfplumber.open(arquivo) as pdf:
                page = pdf.pages[int(p_ini) - 1]
                # Realiza o CROP (Recorte): (x0, top, x1, bottom)
                # Mantemos a largura total (0 a page.width) e cortamos na vertical (y)
                recorte = page.crop((0, y_ini, page.width, y_fim))
                st.image(recorte.to_image(resolution=200).original, use_container_width=True)
except Exception as e:
    st.info("Aguardando PDF e seleção.")
