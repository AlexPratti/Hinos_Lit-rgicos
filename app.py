import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image

# Configuração da página
st.set_page_config(page_title="Gerador de Link Direto", page_icon="🔗")

st.title("🚀 Gerador de QR Code (Link Direto)")
st.write("Insira a URL abaixo. O código garantirá que o celular abra o site diretamente.")

# 1. Entrada de texto com limpeza automática de espaços
url_input = st.text_input("Cole a URL do site aqui:", placeholder="exemplo.com.br").strip()

if url_input:
    # 2. O PULO DO GATO: Garantir o protocolo para o celular reconhecer como LINK
    # Se o usuário não digitar http ou https, o código adiciona automaticamente
    if not url_input.startswith(("http://", "https://")):
        url_final = f"https://{url_input}"
    else:
        url_final = url_input

    # 3. Configuração técnica do QR Code (Alta compatibilidade)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L, # Nível L é melhor para links
        box_size=10,
        border=4,
    )
    
    qr.add_data(url_final)
    qr.make(fit=True)

    # Criar a imagem
    img = qr.make_image(fill_color="black", back_color="white")

    # 4. Processamento da imagem para exibição e download
    buf = BytesIO()
    img.save(buf, format="PNG")
    byte_im = buf.getvalue()

    # Exibição na tela
    st.success(f"Link processado: {url_final}")
    st.image(byte_im, caption="Aponte a câmera para abrir o site diretamente", width=300)

    # Botão de Download
    st.download_button(
        label="📥 Baixar QR Code (PNG)",
        data=byte_im,
        file_name="qrcode_direto.png",
        mime="image/png"
    )

st.divider()
st.info("Dica: Se o seu Redmi ainda mostrar 'Copiar Texto', verifique se a URL digitada não possui caracteres especiais inválidos.")
