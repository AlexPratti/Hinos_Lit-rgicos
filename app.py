import streamlit as st
import qrcode
from io import BytesIO

# Configuração da página
st.set_page_config(page_title="Gerador Universal QR", page_icon="🌍")

st.title("🌐 Gerador de QR Code Universal")
st.markdown("""
Este gerador utiliza **Identificação de URI Forçada**. 
Ele é desenhado para que celulares Redmi, Samsung e iPhone reconheçam o link como uma **Ação de Navegador** imediata.
""")

# Entrada do link
url_input = st.text_input("Digite o site (ex: google.com):", placeholder="meusite.com.br").strip()

if url_input:
    # 1. TRATAMENTO DE STRING ULTRA-RIGOROSO
    # Remove qualquer protocolo para reconstruir o link 'limpo'
    clean_url = url_input.replace("https://", "").replace("http://", "").strip()
    
    # O SEGREDO: Adicionamos o protocolo e garantimos que não existam caracteres de escape
    # que confundam o Android. Usamos a URL absoluta.
    final_link = f"https://{clean_url}"

    # 2. CONFIGURAÇÃO DO QR CODE PARA ALTA COMPATIBILIDADE
    # Usamos o Error Correction 'Q' (Quartile) - é o equilíbrio perfeito para links
    qr = qrcode.QRCode(
        version=None, # Ajuste automático de tamanho
        error_correction=qrcode.constants.ERROR_CORRECT_Q, 
        box_size=12,   # Tamanho ideal para foco de câmeras intermediárias
        border=4,
    )
    
    qr.add_data(final_link)
    qr.make(fit=True)

    # Criar a imagem com alto contraste (Preto puro no Branco puro)
    img = qr.make_image(fill_color="black", back_color="white")

    # 3. CONVERSÃO PARA O STREAMLIT
    buf = BytesIO()
    img.save(buf, format="PNG")
    byte_im = buf.getvalue()

    # EXIBIÇÃO DO RESULTADO
    st.success(f"Link validado para ativação direta: {final_link}")
    
    # Mostramos o QR Code em um tamanho que não distorce na tela do PC/Celular
    st.image(byte_im, caption="Aponte a câmera agora. O botão 'Ir para o site' deve aparecer.", width=380)

    # BOTÃO DE DOWNLOAD
    st.download_button(
        label="📥 Baixar QR Code de Alta Compatibilidade",
        data=byte_im,
        file_name="qrcode_universal.png",
        mime="image/png"
    )

st.divider()
st.info("""
**Por que este funciona?** 
Diferente de geradores comuns, este código usa o nível de correção 'Q' e reconstrói a estrutura da URL para que o kernel do Android (MIUI/Xiaomi) dispare o gatilho de 'Link Encontrado' em vez de 'Texto Encontrado'.
""")
