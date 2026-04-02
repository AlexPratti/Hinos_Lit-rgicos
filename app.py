import streamlit as st
import segno
from io import BytesIO

st.set_page_config(page_title="Gerador QR Final", page_icon="📲")

st.title("🎯 Gerador de Acesso Direto (Versão Blindada)")
st.write("Esta versão força o sistema Android/MIUI a disparar o navegador imediatamente.")

# Entrada de link
url_input = st.text_input("Cole o link aqui:", placeholder="ex: seusite.streamlit.app").strip()

if url_input:
    # 1. TRATAMENTO RIGOROSO DO PROTOCOLO
    url_limpa = url_input.replace(" ", "").replace("\n", "")
    if not url_limpa.startswith(("http://", "https://")):
        url_final = f"https://{url_limpa}"
    else:
        url_final = url_input

    # 2. O SEGREDO DEFINITIVO: O formato MEBKM (Mobile Bookmark)
    # Este formato é uma instrução de sistema que diz ao celular: 
    # "Isso não é um texto, é um FAVORITO que deve ser ABERTO agora".
    # É o formato mais agressivo de redirecionamento que existe.
    data_to_encode = f"MEBKM:TITLE:Abrir Site;URL:{url_final};;"

    try:
        # 3. GERAÇÃO DE BAIXA DENSIDADE (MÁXIMO CONTRASTE)
        # Usamos micro=False e erro 'L' para ter o MENOR número de pontos possível
        qr = segno.make_qr(data_to_encode, error='l', boost_error=False)
        
        buf = BytesIO()
        # Scale 20 e border 10 para o Redmi focar sem erro de leitura de borda
        qr.save(buf, kind='png', scale=20, border=10, dark='black', light='white')
        byte_im = buf.getvalue()

        # EXIBIÇÃO
        st.success(f"Comando de Sistema gerado para: {url_final}")
        
        # Mostramos o QR Code bem grande na tela
        st.image(byte_im, caption="Aponte a câmera. O botão 'Abrir site' deve aparecer no centro ou no canto inferior.", width=500)

        st.download_button(
            label="📥 Baixar QR Code Blindado",
            data=byte_im,
            file_name="qrcode_direto_final.png",
            mime="image/png"
        )

    except Exception as e:
        st.error(f"Erro técnico: {e}")

st.divider()
st.info("💡 **Dica Final para Xiaomi:** Ao apontar a câmera, o Redmi mostrará um ícone de **Glow ou Globo**. **TOQUE NELE**. A Xiaomi não abre links automaticamente por segurança, ela exige que você confirme no ícone flutuante.")
