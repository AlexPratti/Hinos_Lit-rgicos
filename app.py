import streamlit as st
import segno
from io import BytesIO

st.set_page_config(page_title="Gerador QR Oficial", page_icon="🎯")

st.title("🎯 Gerador de QR Code: Acesso Direto")
st.write("Versão de Força Bruta para links do Streamlit (Otimizado para Redmi).")

# Entrada do link
url_input = st.text_input("Cole o link do seu jogo aqui:", value="https://streamlit.app").strip()

if url_input:
    # 1. TRATAMENTO RIGOROSO
    url_final = url_input if url_input.startswith(("http://", "https://")) else f"https://{url_input}"
    
    # 2. O PULO DO GATO PARA XIAOMI: Prefixo de Protocolo URLTO
    # Isso força o Android a disparar o Intent de Navegador, ignorando a trava de texto
    comando_direto = f"URLTO:{url_final}"

    try:
        # 3. GERAÇÃO DE BAIXA DENSIDADE (ERRO L)
        # Usamos o nível de erro mínimo para que os blocos fiquem nítidos
        qr = segno.make_qr(comando_direto, error='l', boost_error=False)
        
        buf = BytesIO()
        # Scale 20 e Border 10 para criar contraste máximo
        qr.save(buf, kind='png', scale=20, border=10)
        byte_im = buf.getvalue()

        # EXIBIÇÃO
        st.success(f"Link de sistema configurado: {url_final}")
        st.image(byte_im, caption="APONTE A CÂMERA E CLIQUE NO ÍCONE DE GLOBO/LINK NO CANTO", width=450)

        st.download_button(
            label="📥 Baixar QR Code Blindado",
            data=byte_im,
            file_name="qrcode_direto.png",
            mime="image/png"
        )

    except Exception as e:
        st.error(f"Erro: {e}")

st.divider()
st.info("💡 **Dica Final:** No Redmi, o botão 'Ir para o site' aparece como um **pequeno ícone de Globo** no canto inferior direito da imagem da câmera. **Toque nele**.")
