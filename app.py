import streamlit as st
import segno
from io import BytesIO

st.set_page_config(page_title="Gerador QR Final", page_icon="📲")

st.title("🎯 Gerador QR: Acesso Direto Garantido")
st.write("Versão otimizada para sensores Xiaomi/Redmi e links longos do Streamlit.")

# Entrada de link
url_input = st.text_input("Cole o link aqui:", placeholder="ex: seusite.streamlit.app").strip()

if url_input:
    # 1. TRATAMENTO DE URL ABSOLUTO
    url_limpa = url_input.replace(" ", "").replace("\n", "")
    if not url_limpa.startswith(("http://", "https://")):
        url_final = f"https://{url_limpa}"
    else:
        url_final = url_limpa

    # 2. O PULO DO GATO DEFINITIVO: O prefixo URLTO:
    # Este prefixo força o Android a entender que o conteúdo É UMA URL, 
    # não importa o quão longo ou estranho seja o link.
    data_to_encode = f"URLTO:{url_final}"

    try:
        # 3. GERAÇÃO DE BAIXA DENSIDADE (MÁXIMO CONTRASTE)
        # Usamos micro=False e erro 'L' para ter o MENOR número de pontos possível
        qr = segno.make_qr(data_to_encode, error='l', boost_error=False)
        
        buf = BytesIO()
        # Scale 20 e border 10 para o Redmi focar instantaneamente sem "ruído"
        qr.save(buf, kind='png', scale=20, border=10, dark='black', light='white')
        byte_im = buf.getvalue()

        # EXIBIÇÃO
        st.success(f"Link de sistema gerado para: {url_final}")
        
        # Mostramos o QR Code bem grande na tela
        st.image(byte_im, caption="Aponte a câmera e toque no botão de link que aparecerá", width=500)

        st.download_button(
            label="📥 Baixar QR Code Infalível",
            data=byte_im,
            file_name="qrcode_direto_final.png",
            mime="image/png"
        )

    except Exception as e:
        st.error(f"Erro técnico: {e}")

st.divider()
st.info("💡 **Dica Final:** Se o seu Redmi mostrar o link num balão flutuante, **toque no ícone do globo ou na seta** ao lado do texto. A Xiaomi exige um toque de confirmação para abrir o navegador.")
