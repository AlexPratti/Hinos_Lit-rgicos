import streamlit as st
import segno
from io import BytesIO

# Configuração da Interface
st.set_page_config(page_title="Gerador QR Universal", page_icon="🌐", layout="centered")

st.title("🎯 Gerador de QR Code: Link Direto")
st.write("Cole qualquer link abaixo para gerar um acesso instantâneo via câmera.")

# Entrada de dados (Campo vazio para você colar o que quiser)
user_input = st.text_input("Cole a URL do site aqui:", placeholder="ex: google.com.br ou seu link do streamlit").strip()

if user_input:
    # 1. TRATAMENTO DE URL (O "Pulo do Gato" para Android/Xiaomi)
    # Remove espaços, quebras de linha e garante o protocolo https://
    url_limpa = user_input.replace(" ", "").replace("\n", "").replace("\r", "")
    
    if not url_limpa.startswith(("http://", "https://")):
        final_url = f"https://{url_limpa}"
    else:
        final_url = url_limpa

    try:
        # 2. GERAÇÃO COM SEGNO (Alta Fidelidade)
        # Usamos scale=15 para que os blocos sejam grandes o suficiente para o foco do Redmi
        qr = segno.make_qr(final_url)
        
        # Criamos o buffer para a imagem PNG
        buf = BytesIO()
        qr.save(buf, kind='png', scale=15, border=4)
        byte_im = buf.getvalue()

        # 3. EXIBIÇÃO NO STREAMLIT
        st.success(f"✅ Link validado: {final_url}")
        
        # Centralizamos a imagem para facilitar o escaneamento direto da tela
        st.image(byte_im, caption="Aponte a câmera e clique em 'Ir para o site'", width=400)

        # BOTÃO DE DOWNLOAD
        st.download_button(
            label="📥 Baixar QR Code (PNG)",
            data=byte_im,
            file_name="qrcode_direto.png",
            mime="image/png"
        )

    except Exception as e:
        st.error(f"Ocorreu um erro ao gerar o QR Code: {e}")

st.divider()
st.info("💡 **Dica para o seu Redmi:** Sempre que colar um link novo, certifique-se de que ele não tenha espaços no final. O botão 'Ir para o site' aparecerá assim que a câmera focar no código.")
