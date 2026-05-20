import streamlit as st
import fitz  # PyMuPDF
import re
from supabase import create_client
import pandas as pd
import io
from docx import Document 

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Hinário Litúrgico", layout="wide")

# Conexão Supabase
try:
    supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])
except Exception as e:
    st.error(f"Erro de conexão com Supabase: {e}")
    st.stop()

CATEGORIAS_ALVO = ["ORANTES", "INICIAIS E FINAIS", "PERDÃO", "GLÓRIA", "DEUS NOS FALA", "SALMO", "ACLAMAÇÃO", "OFERTÓRIO", "LOUVOR", "SANTO", "CORDEIRO", "PAZ", "COMUNHÃO", "BÍBLIA", "CRUZ", "LADAINHAS – SEQUÊNCIAS - PROCLAMAÇÕES", "MARIA", "HINOS DIVERSOS", "PRECES"]

# --- LISTA DE ACORDES PARA TRANSPOSIÇÃO ---
NOTAS_SEMITONS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# --- FUNÇÕES DE PROCESSAMENTO PDF ---
def process_pdf_fitz(file_bytes):
    data = []
    current_cat = "Sem Categoria"
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for i in range(len(doc)):
            page = doc[i]
            text = page.get_text()
            if not text: continue
            for line in text.split('\n'):
                t_limpo = line.strip()
                if t_limpo.upper() in CATEGORIAS_ALVO:
                    current_cat = t_limpo.upper()
                elif re.match(r'^\d+\.', t_limpo) and t_limpo == t_limpo.upper():
                    data.append({"n1": current_cat, "n2": t_limpo, "pag": i + 1})
        doc.close()
        return data
    except Exception as e:
        st.error(f"Erro no processamento do PDF: {e}")
        return []

def save_to_db(data, table_cat, table_cont):
    supabase.table(table_cont).delete().neq("id", 0).execute()
    supabase.table(table_cat).delete().neq("id", 0).execute()
    for cat in CATEGORIAS_ALVO:
        res = supabase.table(table_cat).insert({"nome_nivel1": cat}).execute()
        if res.data:
            res_data = res.data[0] if isinstance(res.data, list) else res.data
            cat_id = res_data['id']
            itens = [{"categoria_id": cat_id, "nome_nivel2": item['n2'], "texto_completo": str(item['pag'])} for item in data if item['n1'] == cat]
            if itens: supabase.table(table_cont).insert(itens).execute()

# --- FUNÇÃO PARA LIMPAR CIFRAS DOCX ---
def limpar_cifras_docx(file):
    doc = Document(file)
    padrao_cifras = r'\b([A-G][b#]?(m|maj|min|7|9|11|13|sus|4|dim|aug|add|6)*)(?=\s|$|/)\b'
    paragraphs = doc.paragraphs
    indices_para_deletar = []

    for i, p in enumerate(paragraphs):
        texto = p.text.strip()
        if not texto:
            continue
            
        acordes = re.findall(padrao_cifras, texto)
        letras_minusculas = len(re.findall(r'[a-z]', texto))
        
        if len(acordes) > 0:
            if letras_minusculas < 3: 
                indices_para_deletar.append(i)
            elif len(acordes) / len(texto.split()) > 0.5:
                indices_para_deletar.append(i)

    for index in sorted(indices_para_deletar, reverse=True):
        p = paragraphs[index]._element
        p.getparent().remove(p)
        p._p = p._element = None

    target = io.BytesIO()
    doc.save(target)
    return target.getvalue()

# --- LÓGICA DE TRANSPOSIÇÃO DE TOM DE CIFRAS ---
def transpor_acorde(acorde, semitons):
    if not acorde or semitons == 0:
        return acorde
    if '/' in acorde:
        partes = acorde.split('/')
        return f"{transpor_acorde(partes[0], semitons)}/{transpor_acorde(partes[1], semitons)}"
        
    match = re.match(r'^([A-G][#b]?)(.*)$', acorde)
    if not match:
        return acorde
    nota_fundamental, complemento = match.groups()
    
    conversao_bemol = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
    if nota_fundamental in conversao_bemol:
        nota_fundamental = conversao_bemol[nota_fundamental]
        
    if nota_fundamental in NOTAS_SEMITONS:
        idx_atual = NOTAS_SEMITONS.index(nota_fundamental)
        novo_idx = (idx_atual + semitons) % 12
        return NOTAS_SEMITONS[novo_idx] + complemento
    return acorde

def processar_e_transpor_por_coordenadas(page, rect, semitons, titulo_hino_selecionado):
    words = page.get_text("words", clip=rect)
    if not words:
        return ""
        
    # 1. Agrupa as palavras por linhas geométricas (tolerância de 5 pixels verticais)
    linhas_dict = {}
    for w in words:
        y0 = w[1]
        encontrado = False
        for y_chave in list(linhas_dict.keys()):
            if abs(y_chave - y0) < 5:
                linhas_dict[y_chave].append(w)
                encontrado = True
                break
        if not encontrado:
            linhas_dict[y0] = [w]
            
    padrao_acorde_estrito = r'^([A-G][b#]?(?:m|maj|min|7|9|11|13|sus|4|dim|aug|add|6)*(?:/[A-G][b#]?)?)$'
    linhas_ordenadas = sorted(linhas_dict.keys())
    
    # 2. Estrutura as linhas identificando o tipo (Cifra, Letra ou Título)
    linhas_estruturadas = []
    for y in linhas_ordenadas:
        palavras_da_linha = sorted(linhas_dict[y], key=lambda x: x[0])
        texto_linha = " ".join([w[4] for w in palavras_da_linha]).strip()
        
        # Ignora/protege títulos ou cabeçalhos
        if (titulo_hino_selecionado in texto_linha or 
            re.match(r'^\d+\.\s+[A-ZÁÉÍÓÚÂÊÔÇ\s,!\-]+$', texto_linha)):
            linhas_estruturadas.append({"tipo": "titulo", "texto": texto_linha, "palavras": palavras_da_linha})
            continue
            
        total_p = len(palavras_da_linha)
        chords_count = sum(1 for w in palavras_da_linha if re.match(padrao_acorde_estrito, w[4].strip()))
        eh_cifra = (chords_count / total_p >= 0.75) if total_p > 0 else False
        
        linhas_estruturadas.append({
            "tipo": "cifra" if eh_cifra else "letra",
            "texto": texto_linha,
            "palavras": palavras_da_linha
        })

    # 3. Reconstrói o hino aplicando o alinhamento relativo por caractere
    texto_final = []
    
    for idx, bloco in enumerate(linhas_estruturadas):
        if bloco["tipo"] == "titulo":
            texto_final.append(bloco["texto"])
            continue
            
        if bloco["tipo"] == "letra":
            # Se for linha de texto comum, apenas adicionamos ela limpa
            texto_final.append(bloco["texto"])
            continue
            
        if bloco["tipo"] == "cifra":
            # Encontra a linha de letra correspondente logo abaixo para servir de régua métrica
            proxima_letra = None
            for posterior in linhas_estruturadas[idx+1:]:
                if posterior["tipo"] == "letra":
                    proxima_letra = posterior
                    break
            
            if not proxima_letra:
                # Caso não exista linha de texto abaixo (fim do hino), monta pelo método antigo simplificado
                linha_cifra_avulsa = ""
                ultimo_x = rect.x0
                for w in bloco["palavras"]:
                    espacos = int((w[0] - ultimo_x) / 5.6)
                    linha_cifra_avulsa += (" " * max(1, espacos)) + transpor_acorde(w[4].strip(), semitons)
                    ultimo_x = w[2]
                texto_final.append(linha_cifra_avulsa)
                continue
                
            # Mapeamento Geométrico Inteligente baseado na linha de texto de baixo
            palavras_texto = proxima_letra["palavras"]
            x_inicio_texto = palavras_texto[0][0]
            x_fim_texto = palavras_texto[-1][2]
            largura_total_texto_pdf = max(1, x_fim_texto - x_inicio_texto)
            num_caracteres_texto = len(proxima_letra["texto"])
            
            # Fator de conversão: quantos pixels do PDF equivalem a 1 caractere de texto
            pixels_por_caractere = largura_total_texto_pdf / num_caracteres_texto
            
            linha_cifra_construida = [" "] * (num_caracteres_texto + 30)
            
            for w in bloco["palavras"]:
                x0_cifra = w[0]
                acorde_transposto = transpor_acorde(w[4].strip(), semitons)
                
                # Descobre em qual índice de caractere o acorde deve pousar
                if x0_cifra <= x_inicio_texto:
                    indice_caractere = 0
                else:
                    distancia_pixels = x0_cifra - x_inicio_texto
                    indice_caractere = int(round(distancia_pixels / pixels_por_caractere))
                
                # Garante que não vai estourar o vetor à esquerda
                indice_caractere = max(0, indice_caractere)
                
                # Insere os caracteres do acorde um a um no array de strings
                for c_idx, caractere_nota in enumerate(acorde_transposto):
                    posicao_alvo = indice_caractere + c_idx
                    if posicao_alvo < len(linha_cifra_construida):
                        linha_cifra_construida[posicao_alvo] = caractere_nota
            
            # Junta os caracteres ignorando posições vazias à direita
            texto_linha_cifra = "".join(linha_cifra_construida).rstrip()
            texto_final.append(texto_linha_cifra)
            
    return "\n".join(texto_final)


# --- INTERFACE ---
tab_cifras, tab_letras, tab_up_cifras, tab_up_letras, tab_util = st.tabs([
    "🎸 Hinos com Cifras", "📖 Hinos (Letras)", "⚙️ Upload Cifras", "⚙️ Upload Letras", "🛠️ Limpar Cifras"
])

def render_hino_interface(bucket, file_path, table_cat, table_cont, key_suffix):
    try:
        res_cat = supabase.table(table_cat).select("*").order("nome_nivel1").execute()
        if res_cat.data:
            df_cat = pd.DataFrame(res_cat.data)
            c1, c2 = st.columns(2)
            with c1:
                sel_cat = st.selectbox("Categoria", df_cat['nome_nivel1'], key=f"cat_{key_suffix}")
                cat_id_row = df_cat[df_cat['nome_nivel1'] == sel_cat]['id'].values
                if len(cat_id_row) > 0:
                    cat_id = int(cat_id_row[0])
                else:
                    st.stop()
            
            hinos_res = supabase.table(table_cont).select("*").eq("categoria_id", cat_id).execute().data
            if hinos_res:
                hinos_ord = sorted(hinos_res, key=lambda x: int(re.search(r'\d+', x['nome_nivel2']).group()) if re.search(r'\d+', x['nome_nivel2']) else 0)
                with c2:
                    sel_hino = st.selectbox("Hino", [h['nome_nivel2'] for h in hinos_ord], key=f"hino_{key_suffix}")
                
                pdf_res = supabase.storage.from_(bucket).download(file_path)
                if pdf_res:
                    hino_obj = next(h for h in hinos_res if h['nome_nivel2'] == sel_hino)
                    p_num = int(hino_obj['texto_completo']) - 1
                    doc = fitz.open(stream=pdf_res, filetype="pdf")
                    page = doc[p_num]
                    text_instances = page.search_for(sel_hino)
                    y_ini = text_instances[0].y0 if text_instances else 0
                    y_fim = page.rect.height
                    
                    blocks = page.get_text("blocks")
                    for b in blocks:
                        if b[1] > y_ini + 10:
                            txt_block = b[4].strip()
                            if re.match(r'^\d+\.', txt_block) or txt_block.upper() in CATEGORIAS_ALVO:
                                y_fim = b[1]
                                break
                    
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=fitz.Rect(0, max(0, y_ini-15), page.rect.width, y_fim))
                    st.divider()
                    st.caption("### 📋 Modelo Original")
                    st.image(pix.tobytes("png"), use_container_width=True)
                    
                    if key_suffix == "cifras":
                        st.divider()
                        st.subheader("🔄 Transposição de Tom")
                        
                        opcoes_tons = {
                            "Original": 0, "Aumentar ½ Tom (+1)": 1, "Aumentar 1 Tom (+2)": 2, "Aumentar 1½ Tom (+3)": 3,
                            "Aumentar 2 Tons (+4)": 4, "Aumentar 2½ Tons (+5)": 5, "Aumentar 3 Tons (+6)": 6,
                            "Diminuir ½ Tom (-1)": -1, "Diminuir 1 Tom (-2)": -2, "Diminuir 1½ Tom (-3)": -3,
                            "Diminuir 2 Tons (-4)": -4, "Diminuir 2½ Tons (-5)": -5, "Diminuir 3 Tons (-6)": -6
                        }
                        
                        tom_selecionado = st.selectbox("Selecione o novo tom para readequar as cifras:", list(opcoes_tons.keys()), key="seletor_tom")
                        deslocamento_semitons = opcoes_tons[tom_selecionado]
                        
                        retangulo_hino = fitz.Rect(0, max(0, y_ini-15), page.rect.width, y_fim)
                        texto_final_transposto = processar_e_transpor_por_coordenadas(page, retangulo_hino, deslocamento_semitons, sel_hino)
                        
                        st.caption("### 🎵 Cifras Reajustadas")
                        st.code(texto_final_transposto, language="text")
                        
                    doc.close()
    except Exception as e: st.error(f"Erro: {e}")

with tab_cifras: render_hino_interface("hinarios", "hinario_atual.pdf", "hinos_categorias", "hinos_conteudos", "cifras")
with tab_letras: render_hino_interface("letras", "hinario_letras.pdf", "hinos_categorias_letras", "hinos_conteudos_letras", "letras")

with tab_up_cifras:
    st.subheader("Configuração Cifras")
    n_c = st.file_uploader("PDF Cifras", type="pdf", key="f_c")
    if st.button("🚀 Atualizar Cifras") and n_c:
        b = n_c.read()
        supabase.storage.from_("hinarios").upload(path="hinario_atual.pdf", file=b, file_options={"x-upsert": "true", "content-type": "application/pdf"})
        d = process_pdf_fitz(b)
        if d: save_to_db(d, "hinos_categorias", "hinos_conteudos"); st.success("OK!"); st.rerun()

with tab_up_letras:
    st.subheader("Configuração Letras")
    n_l = st.file_uploader("PDF Letras", type="pdf", key="f_l")
    if st.button("🚀 Atualizar Letras") and n_l:
        b = n_l.read()
        supabase.storage.from_("letras").upload(path="hinario_letras.pdf", file=b, file_options={"x-upsert": "true", "content-type": "application/pdf"})
        d = process_pdf_fitz(b)
        if d: save_to_db(d, "hinos_categorias_letras", "hinos_conteudos_letras"); st.success("OK!"); st.rerun()

with tab_util:
    st.subheader("Remover Cifras de DOCX")
    arquivo_docx = st.file_uploader("Selecione o arquivo DOCX", type="docx")
    if arquivo_docx:
        if st.button("✨ Limpar Documento"):
            resultado_bytes = limpar_cifras_docx(arquivo_docx)
            st.download_button(label="📥 Baixar DOCX Sem Cifras", data=resultado_bytes, file_name="LITURGICOS_SEM_CIFRAS.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
