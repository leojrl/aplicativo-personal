import streamlit as st
import streamlit.components.v1 as components
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import json
import os
import sys
import re
import base64
import hashlib
import hmac
import secrets
from datetime import date
from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    from fundo_padrao import FUNDO_PADRAO_B64
except Exception:
    FUNDO_PADRAO_B64 = None

# ==========================================
# CONFIGURAÇÕES E DADOS BASE
# ==========================================
st.set_page_config(
    page_title="KW Alta Performance",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

DIRETORIO_APP = os.path.dirname(os.path.abspath(__file__))
if DIRETORIO_APP not in sys.path:
    sys.path.insert(0, DIRETORIO_APP)

ARQUIVO_DADOS = os.path.join(DIRETORIO_APP, "dados_treinos.json")
ARQUIVO_USUARIOS = os.path.join(DIRETORIO_APP, "usuarios.json")
ARQUIVO_CATALOGO_VIDEOS = os.path.join(DIRETORIO_APP, "catalogo_videos.json")
DIRETORIO_VIDEOS = os.path.join(DIRETORIO_APP, "videos_exercicios")
os.makedirs(DIRETORIO_VIDEOS, exist_ok=True)
CAMINHO_LOGO = os.path.join(DIRETORIO_APP, "1000370127.jpg")

def assegurar_arquivo_logo():
    """Garante que o arquivo de logo/fundo exista no servidor mesmo se não estiver no repositório Git."""
    try:
        if not os.path.isfile(CAMINHO_LOGO) and FUNDO_PADRAO_B64:
            with open(CAMINHO_LOGO, "wb") as f:
                f.write(base64.b64decode(FUNDO_PADRAO_B64))
    except Exception:
        pass

assegurar_arquivo_logo()
def checar_firestore_ativo():
    if os.getenv("FIRESTORE_ENABLED", "").lower() in {"1", "true", "yes"}:
        return True
    try:
        if hasattr(st, "secrets"):
            if "FIRESTORE_ENABLED" in st.secrets and str(st.secrets["FIRESTORE_ENABLED"]).lower() in {"1", "true", "yes"}:
                return True
            if "project_id" in st.secrets and "private_key" in st.secrets:
                return True
            for chave in ["gcp_service_account", "firebase", "firestore", "google_credentials"]:
                if chave in st.secrets:
                    return True
    except Exception:
        pass
    # Se o arquivo local de credenciais do Firebase existir, ativa o Firestore automaticamente
    caminho_cred = os.path.join(DIRETORIO_APP, "kwborachoque-313e3-firebase-adminsdk-fbsvc-8b0fbe3d51.json")
    if os.path.isfile(caminho_cred):
        return True
    return False

USAR_FIRESTORE = checar_firestore_ativo()
TAMANHO_MAXIMO_FOTO_PERFIL = 300 * 1024

# Somente Leo e William são administradores. Todos os demais são alunos/atletas.
ADMINS_AUTORIZADOS = {"leo", "william", "wilian", "willian"}

def eh_administrador(nome_usuario):
    """Retorna True ESTRITAMENTE para os administradores autorizados: Leo e William."""
    if not nome_usuario or not isinstance(nome_usuario, str):
        return False
    return nome_usuario.strip().lower() in ADMINS_AUTORIZADOS

def injetar_css(codigo_css):
    """Injeta código CSS com compatibilidade universal para todas as versões do Streamlit (local e servidor)."""
    tag_style = f"<style>\n{codigo_css}\n</style>"
    try:
        st.markdown(tag_style, unsafe_allow_html=True)
    except Exception:
        pass
    try:
        if hasattr(st, "html"):
            st.html(tag_style)
    except Exception:
        pass

MODALIDADES_ICONES = {
    "Futebol": "⚽ Futebol",
    "Futevôlei": "🏐 Futevôlei",
    "Beach Tênis": "🎾 Beach Tênis",
    "Tênis": "🎾 Tênis",
    "Basquete": "🏀 Basquete"
}

MODALIDADES_EXERCICIOS = {
    "Futebol": ["Passe curto", "Passe longo", "Finalização", "Controle de bola", "Drible", "Trabalho de pés", "Condicionamento físico"],
    "Futevôlei": ["Saque", "Recepção de peito", "Recepção de coxa", "Levantamento", "Ataque (Pingada)", "Ataque (Forte)", "Defesa"],
    "Beach Tênis": ["Saque", "Voleio de Forehand", "Voleio de Backhand", "Smash", "Lob", "Devolução", "Movimentação em areia"],
    "Tênis": ["Saque", "Forehand", "Backhand", "Smash", "Slice", "Footwork", "Drop Shot", "Topspin", "Devolução", "Rally de Fundo"],
    "Basquete": ["Arremesso (Jump)", "Lance Livre", "Bandeja", "Drible", "Passe de peito", "Passe picado", "Rebote"]
}

@st.cache_data(show_spinner=False)
def carregar_imagem_base64(caminho, max_dim=(1920, 1920), qualidade=85):
    """Carrega imagem em Base64 com suporte a cache, redimensionamento e fallback nativo."""
    if not caminho or not os.path.isfile(caminho):
        return FUNDO_PADRAO_B64
    try:
        imagem = Image.open(caminho).convert("RGB")
        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", getattr(Image, "ANTIALIAS", None))
        if resample:
            imagem.thumbnail(max_dim, resample)
        else:
            imagem.thumbnail(max_dim)
        buffer = BytesIO()
        imagem.save(buffer, format="JPEG", quality=qualidade, optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception:
        return FUNDO_PADRAO_B64

def obter_caminho_foto_login():
    """Localiza a imagem de fundo de forma resiliente em qualquer sistema de arquivos (Windows/Linux/Streamlit Cloud)."""
    candidatos_nomes = [
        "foto_login.jpg", "foto_login.png", "foto_login.jpeg", "foto_login.webp",
        "fundo_login.jpg", "fundo_login.png", "fundo_login.jpeg", "fundo_login.webp",
        "login_bg.jpg", "login_bg.png", "login_bg.jpeg", "login_bg.webp",
        "fundo.jpg", "fundo.png", "fundo.jpeg",
        "1000370127.jpg", "1000370127.png", "1000370127.jpeg"
    ]
    diretorios_busca = [
        DIRETORIO_APP,
        os.getcwd(),
        os.path.join(DIRETORIO_APP, "assets"),
        os.path.join(DIRETORIO_APP, "static"),
        os.path.join(DIRETORIO_APP, "images")
    ]
    # Busca direta por arquivo existente
    for d in diretorios_busca:
        if not os.path.isdir(d):
            continue
        for nome in candidatos_nomes:
            c = os.path.join(d, nome)
            if os.path.isfile(c):
                return c

    # Busca insensível a maiúsculas/minúsculas para servidores Linux
    for d in diretorios_busca:
        if not os.path.isdir(d):
            continue
        try:
            arquivos = os.listdir(d)
            for arq in arquivos:
                arq_low = arq.lower()
                for c in candidatos_nomes:
                    if arq_low == c.lower():
                        c_path = os.path.join(d, arq)
                        if os.path.isfile(c_path):
                            return c_path
        except Exception:
            pass

    return CAMINHO_LOGO if os.path.isfile(CAMINHO_LOGO) else None

LOGO_BASE64 = carregar_imagem_base64(CAMINHO_LOGO, (1024, 1024), 88) or FUNDO_PADRAO_B64
FUNDO_LOGO_B64 = carregar_imagem_base64(obter_caminho_foto_login() or CAMINHO_LOGO, (1400, 1400), 85) or LOGO_BASE64 or FUNDO_PADRAO_B64

def injetar_fundo_dashboard():
    logo_b64 = carregar_imagem_base64(CAMINHO_LOGO, (1400, 1400), 85) or FUNDO_LOGO_B64 or FUNDO_PADRAO_B64
    fundo_pag_b64 = carregar_imagem_base64(obter_caminho_foto_login() or CAMINHO_LOGO, (1600, 1600), 85) or logo_b64 or FUNDO_PADRAO_B64
    if fundo_pag_b64:
        injetar_css(
            f"""
            /* 1. FUNDO DE TELA DE TODAS AS PÁGINAS COM A LOGO DO PROJETO (UNIVERSAL) */
            .stApp::before {{
                content: "" !important;
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                bottom: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                background-color: #05070d !important;
                background-image:
                    radial-gradient(circle at 50% 50%, rgba(7, 11, 19, 0.45) 0%, rgba(5, 8, 15, 0.65) 70%, rgba(4, 6, 12, 0.82) 100%),
                    url('data:image/jpeg;base64,{fundo_pag_b64}') !important;
                background-position: center center, center center !important;
                background-repeat: no-repeat, no-repeat !important;
                background-size: cover, contain !important;
                z-index: 0 !important;
                pointer-events: none !important;
            }}

            html, body, .stApp,
            [data-testid="stApp"],
            [data-testid="stAppViewContainer"],
            .stAppViewContainer {{
                background-color: #05070d !important;
                background-image:
                    radial-gradient(circle at 50% 50%, rgba(7, 11, 19, 0.45) 0%, rgba(5, 8, 15, 0.65) 70%, rgba(4, 6, 12, 0.82) 100%),
                    url('data:image/jpeg;base64,{fundo_pag_b64}') !important;
                background-position: center center, center center !important;
                background-repeat: no-repeat, no-repeat !important;
                background-attachment: fixed, fixed !important;
                background-size: cover, contain !important;
            }}

            section.main,
            .main,
            [data-testid="stMain"],
            .stMain,
            [data-testid="stMainBlockContainer"],
            .stMainBlockContainer,
            div[data-testid="stAppViewContainer"] > section,
            div[data-testid="stAppViewContainer"] > div {{
                background: transparent !important;
                background-color: transparent !important;
                position: relative !important;
                z-index: 1 !important;
            }}

            /* 2. FUNDO DO MENU LATERAL (SIDEBAR) COM A LOGO DO PROJETO */
            section[data-testid="stSidebar"],
            section[data-testid="stSidebar"] > div:first-child {{
                background-color: #070a12 !important;
                background-image:
                    linear-gradient(180deg, rgba(7, 10, 18, 0.78) 0%, rgba(12, 18, 32, 0.82) 50%, rgba(7, 10, 18, 0.88) 100%),
                    url('data:image/jpeg;base64,{logo_b64}') !important;
                background-position: center center, center center !important;
                background-repeat: no-repeat, no-repeat !important;
                background-size: cover, contain !important;
            }}

            /* 3. FUNDO DOS MENUS, EXPANDERS, ABAS E PAINÉIS COM A LOGO DO PROJETO */
            [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="stExpander"],
            div[data-testid="stPopoverBody"] {{
                background-color: rgba(11, 16, 28, 0.76) !important;
                background-image:
                    linear-gradient(145deg, rgba(14, 20, 34, 0.78) 0%, rgba(8, 12, 22, 0.84) 100%),
                    url('data:image/jpeg;base64,{logo_b64}') !important;
                background-position: center center, center center !important;
                background-repeat: no-repeat, no-repeat !important;
                background-size: cover, contain !important;
                backdrop-filter: blur(8px) !important;
                -webkit-backdrop-filter: blur(8px) !important;
            }}

            [data-testid="stExpander"] details,
            [data-testid="stExpander"] details summary {{
                background: rgba(10, 15, 26, 0.55) !important;
            }}

            [data-testid="stTabs"] [role="tablist"] {{
                background-image:
                    linear-gradient(90deg, rgba(10, 15, 26, 0.80) 0%, rgba(17, 24, 39, 0.80) 100%),
                    url('data:image/jpeg;base64,{logo_b64}') !important;
                background-position: center center !important;
                background-repeat: no-repeat !important;
                background-size: cover !important;
            }}

            [data-testid="stMetric"] {{
                background-image:
                    linear-gradient(135deg, rgba(16, 23, 38, 0.80) 0%, rgba(10, 15, 26, 0.86) 100%),
                    url('data:image/jpeg;base64,{logo_b64}') !important;
                background-position: center center, right center !important;
                background-repeat: no-repeat, no-repeat !important;
                background-size: cover, contain !important;
            }}

            /* 4. FUNDO DOS MENUS SUSPENSOS (DROPDOWNS / SELECTS) COM A LOGO SUAVE E LETRA PRETA */
            div[data-baseweb="popover"],
            div[data-baseweb="menu"],
            ul[role="listbox"] {{
                background-color: #ffffff !important;
                background-image:
                    linear-gradient(rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.92)),
                    url('data:image/jpeg;base64,{logo_b64}') !important;
                background-position: center center, center center !important;
                background-repeat: no-repeat, no-repeat !important;
                background-size: cover, contain !important;
            }}
            li[role="option"] {{
                background-color: transparent !important;
            }}
            li[role="option"]:hover,
            li[role="option"][aria-selected="true"] {{
                background-color: rgba(254, 240, 138, 0.88) !important;
            }}
            """
        )

# ==========================================
# ESTILIZAÇÃO CSS GLOBAL (CAMPOS E MENUS COM LETRA PRETA)
# ==========================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@600;700;800;900&display=swap');

    :root {
        --kn-bg-dark: #070a10;
        --kn-card-bg: rgba(17, 24, 39, 0.92);
        --kn-border: rgba(255, 255, 255, 0.08);
        --kn-border-accent: rgba(245, 196, 0, 0.25);
        --kn-accent: #f5c400;
        --kn-cyan: #38bdf8;
        --kn-text-title: #ffffff;
        --kn-text-main: #f1f5f9;
        --kn-text-muted: #94a3b8;
    }

    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--kn-text-main);
    }

    h1, h2, h3, h4 {
        font-family: 'Outfit', 'Plus Jakarta Sans', sans-serif !important;
        letter-spacing: -0.02em;
        color: var(--kn-text-title) !important;
    }

    /* Fundo Studio / High-Performance Atmosphere */
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section.main {
        background: transparent !important;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    [data-testid="stAppViewContainer"] main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1260px;
    }

    /* Barra Lateral */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #090d15 0%, #0f172a 50%, #090d16 100%) !important;
        border-right: 1px solid var(--kn-border) !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.45);
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: var(--kn-text-muted) !important;
    }

    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #e2e8f0 !important;
        font-weight: 700;
        font-size: 0.9rem;
    }

    /* ============================================================
       MENUS E CAMPOS DE DIGITAÇÃO: TEXTO EM COR PRETO E FUNDO BRANCO
       ============================================================ */
    input, textarea {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        caret-color: #000000 !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
    }

    div[data-baseweb="input"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] {
        background-color: #ffffff !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 12px !important;
        transition: all 0.2s ease !important;
    }

    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"] > div:focus-within,
    div[data-baseweb="textarea"]:focus-within {
        border-color: #f5c400 !important;
        box-shadow: 0 0 0 3px rgba(245, 196, 0, 0.35) !important;
    }

    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {
        color: #000000 !important;
        font-weight: 600;
    }

    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[role="listbox"],
    li[role="option"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    li[role="option"] span,
    li[role="option"] div,
    li[role="option"] p {
        color: #000000 !important;
        font-weight: 600 !important;
    }

    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {
        background-color: #fef08a !important;
        color: #000000 !important;
    }

    ::placeholder {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        font-weight: 400 !important;
    }

    div[data-baseweb="tag"] {
        background-color: #fef08a !important;
        border: 1px solid #facc15 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="tag"] span {
        color: #000000 !important;
        font-weight: 700 !important;
    }
    div[data-baseweb="tag"] svg {
        fill: #000000 !important;
    }

    div[data-testid="stPopoverBody"] {
        background-color: var(--kn-card-bg) !important;
        border: 1px solid var(--kn-border) !important;
        border-radius: 14px !important;
    }

    /* Cards e Containers Modernos com Glassmorphism */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(145deg, rgba(18, 25, 41, 0.94) 0%, rgba(11, 16, 26, 0.96) 100%) !important;
        border: 1px solid var(--kn-border-accent) !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 32px rgba(0, 0, 0, 0.42) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(245, 196, 0, 0.38) !important;
        box-shadow: 0 14px 40px rgba(0, 0, 0, 0.55), 0 0 20px rgba(245, 196, 0, 0.08) !important;
    }

    /* Métricas / KPI Cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(20, 28, 46, 0.92) 0%, rgba(13, 18, 30, 0.95) 100%) !important;
        border: 1px solid rgba(245, 196, 0, 0.22) !important;
        border-radius: 18px !important;
        padding: 1.2rem 1.3rem !important;
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.35) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        position: relative;
        overflow: hidden;
    }

    [data-testid="stMetric"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--kn-accent) 0%, var(--kn-cyan) 100%);
    }

    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 1.9rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--kn-text-muted) !important;
        font-size: 0.82rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        font-weight: 700 !important;
    }

    /* Abas de Navegação */
    [data-testid="stTabs"] [role="tablist"] {
        gap: 0.6rem !important;
        border-bottom: 1px solid var(--kn-border) !important;
        padding-bottom: 0.5rem !important;
        margin-bottom: 1.5rem !important;
    }

    [data-testid="stTabs"] button[role="tab"] {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 14px !important;
        padding: 0.6rem 1.35rem !important;
        color: var(--kn-text-muted) !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
    }

    [data-testid="stTabs"] button[role="tab"]:hover {
        background: rgba(245, 196, 0, 0.1) !important;
        border-color: rgba(245, 196, 0, 0.25) !important;
        color: #ffffff !important;
    }

    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(245, 196, 0, 0.18) 0%, rgba(234, 179, 8, 0.10) 100%) !important;
        border: 1px solid var(--kn-accent) !important;
        color: var(--kn-accent) !important;
        box-shadow: 0 4px 18px rgba(245, 196, 0, 0.22) !important;
    }

    /* Expanders */
    [data-testid="stExpander"] {
        background: var(--kn-card-bg) !important;
        border: 1px solid var(--kn-border-accent) !important;
        border-radius: 18px !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.28) !important;
        margin-bottom: 1rem !important;
        overflow: hidden !important;
    }

    [data-testid="stExpander"] details summary {
        padding: 1rem 1.3rem !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        color: #ffffff !important;
        background: var(--kn-card-bg) !important;
    }

    [data-testid="stExpander"] details summary svg {
        color: var(--kn-accent) !important;
    }

    /* Botões Modernos com Efeito Glow */
    div[data-testid="stButton"] > button {
        border-radius: 14px !important;
        font-weight: 700 !important;
        padding: 0.65rem 1.4rem !important;
        transition: all 0.2s ease !important;
        min-height: 42px !important;
    }

    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #f5c400 0%, #eab308 100%) !important;
        border: none !important;
        color: #070a10 !important;
        box-shadow: 0 4px 20px rgba(245, 196, 0, 0.35) !important;
    }

    div[data-testid="stButton"] > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px rgba(245, 196, 0, 0.5) !important;
    }

    div[data-testid="stButton"] > button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid var(--kn-border-accent) !important;
        color: #f1f5f9 !important;
    }

    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background: rgba(245, 196, 0, 0.1) !important;
        border-color: var(--kn-accent) !important;
    }

    /* Vídeos e Frames */
    iframe, video, [data-testid="stVideo"] {
        border-radius: 16px !important;
        border: 1px solid var(--kn-border-accent) !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45) !important;
        width: 100% !important;
    }

    /* Estilização da Foto Circular do Atleta via st.image */
    .kn-photo-frame img {
        border-radius: 50% !important;
        border: 4px solid #f5c400 !important;
        box-shadow: 0 10px 30px rgba(245, 196, 0, 0.45) !important;
        margin: 0 auto !important;
        display: block !important;
        object-fit: cover !important;
        aspect-ratio: 1 / 1 !important;
    }

    .kn-athlete-placeholder {
        width: 140px;
        height: 140px;
        border-radius: 50%;
        background: #131a29;
        border: 3.5px dashed rgba(245, 196, 0, 0.55);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3.8rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
        margin: 0 auto 0.8rem;
    }

    .kn-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        background: rgba(245, 196, 0, 0.12);
        color: #f5c400;
        border: 1px solid rgba(245, 196, 0, 0.32);
        box-shadow: 0 2px 10px rgba(245, 196, 0, 0.12);
    }

    .kn-chip-cyan {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        background: rgba(56, 189, 248, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.32);
        box-shadow: 0 2px 10px rgba(56, 189, 248, 0.12);
    }

    .kn-data-grid {
        display: flex;
        justify-content: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 1.1rem;
        width: 100%;
    }

    .kn-data-card {
        flex: 1 1 120px;
        min-width: 110px;
        max-width: 150px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 14px;
        padding: 10px 12px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .kn-data-card:hover {
        transform: translateY(-2px);
        border-color: rgba(245, 196, 0, 0.3);
    }

    .kn-data-label {
        font-size: 0.72rem;
        color: #94a3b8;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.05em;
        margin-bottom: 3px;
    }

    .kn-data-value {
        font-size: 1.25rem;
        font-weight: 800;
        color: #ffffff;
        font-family: 'Outfit', sans-serif;
    }

    .kn-stat-badge {
        display: flex;
        flex-direction: column;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid var(--kn-border-accent);
        border-radius: 14px;
        padding: 10px 16px;
        min-width: 110px;
    }

    .kn-coach-note {
        background: rgba(245, 196, 0, 0.07);
        border-left: 4px solid #f5c400;
        padding: 12px 16px;
        border-radius: 0 12px 12px 0;
        margin-top: 12px;
        color: #f1f5f9;
        font-size: 0.95rem;
        line-height: 1.5;
    }

    .kn-sidebar-user {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid var(--kn-border-accent);
        border-radius: 16px;
        padding: 14px 16px;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .kn-success-card {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.35);
        border-radius: 18px;
        padding: 1.5rem;
        display: flex;
        align-items: center;
        gap: 16px;
        margin-top: 14px;
    }

    .kn-empty-video {
        background: rgba(255, 255, 255, 0.02);
        border: 1px dashed rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 2.5rem 1.5rem;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }

    /* ============================================================
       OTIMIZAÇÕES RESPONSIVAS PARA CELULAR (SMARTPHONES E TABLETS)
       ============================================================ */
    @media (max-width: 768px) {
        [data-testid="stAppViewContainer"] main .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
            padding-top: 1rem !important;
            padding-bottom: 2.5rem !important;
        }

        h1 {
            font-size: 1.8rem !important;
        }
        h2 {
            font-size: 1.45rem !important;
        }
        h3 {
            font-size: 1.2rem !important;
        }

        .kn-data-grid {
            gap: 8px !important;
        }

        .kn-data-card {
            flex: 1 1 45% !important;
            max-width: 48% !important;
            padding: 8px 10px !important;
        }

        .kn-data-value {
            font-size: 1.15rem !important;
        }

        .kn-photo-frame img {
            width: 125px !important;
            height: 125px !important;
        }

        .kn-athlete-placeholder {
            width: 120px !important;
            height: 120px !important;
            font-size: 3rem !important;
        }

        div[data-testid="stButton"] > button {
            min-height: 44px !important;
            padding: 0.55rem 0.9rem !important;
            font-size: 0.88rem !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }

        [data-testid="stTabs"] button[role="tab"] {
            padding: 0.5rem 0.9rem !important;
            font-size: 0.88rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# POLIMENTO VISUAL MOBILE-FIRST (APP-LIKE)
# ==========================================
injetar_css(
    """
    :root { color-scheme: dark; }

    /* Rolagem suave, sem zoom de toque e sem barra horizontal */
    html, body { -webkit-text-size-adjust: 100%; scroll-behavior: smooth; overflow-x: hidden; }
    * { -webkit-tap-highlight-color: transparent; }

    /* Botões: pílula moderna com gradiente e feedback ao toque */
    div[data-testid="stButton"] > button,
    div[data-testid="stFormSubmitButton"] > button,
    div[data-testid="stDownloadButton"] > button {
        border-radius: 14px !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em;
        transition: transform .12s ease, box-shadow .2s ease, filter .2s ease !important;
    }
    div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #ffd43b 0%, #f5a800 100%) !important;
        color: #111827 !important;
        border: none !important;
        box-shadow: 0 6px 18px rgba(245, 168, 0, 0.35) !important;
    }
    div[data-testid="stButton"] > button:active,
    div[data-testid="stFormSubmitButton"] > button:active {
        transform: scale(0.97);
        filter: brightness(0.95);
    }

    /* Abas estilo "segmented control" */
    [data-testid="stTabs"] [role="tablist"] {
        gap: 6px;
        background: rgba(255,255,255,0.05);
        padding: 5px;
        border-radius: 16px;
        border-bottom: none !important;
        overflow-x: auto;
        scrollbar-width: none;
    }
    [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar { display: none; }
    [data-testid="stTabs"] button[role="tab"] {
        border-radius: 12px !important;
        white-space: nowrap;
        transition: background .2s ease, color .2s ease;
    }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(245,196,0,0.22), rgba(56,189,248,0.14)) !important;
        color: #ffd43b !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"],
    [data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }

    /* Expanders como cartões */
    [data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 16px !important;
        background: rgba(15, 22, 36, 0.7) !important;
        overflow: hidden;
    }

    /* Barra de progresso com gradiente */
    [data-testid="stProgress"] div[role="progressbar"] > div,
    [data-testid="stProgress"] > div > div > div > div {
        background: linear-gradient(90deg, #f5c400, #38bdf8) !important;
        border-radius: 999px !important;
    }

    /* Imagens e vídeos arredondados */
    [data-testid="stImage"] img, [data-testid="stVideo"] video, iframe {
        border-radius: 16px !important;
    }

    @media (max-width: 768px) {
        [data-testid="stAppViewContainer"] main .block-container {
            padding: 0.9rem 0.8rem 5rem 0.8rem !important;
        }
        h1 { font-size: 1.6rem !important; line-height: 1.2 !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.1rem !important; }

        /* Colunas empilham em largura total (cards legíveis) */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.6rem !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width: calc(50% - 0.6rem) !important;
            flex: 1 1 calc(50% - 0.6rem) !important;
        }

        /* Cartões mais compactos e com cantos amplos */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 18px !important;
            padding: 0.2rem !important;
        }
        [data-testid="stMetric"] { padding: 0.8rem 0.9rem !important; border-radius: 16px !important; }

        /* Alvos de toque confortáveis e sem zoom do iOS */
        input, textarea, div[data-baseweb="select"] * { font-size: 16px !important; }
        div[data-baseweb="input"], div[data-baseweb="select"] > div { min-height: 48px !important; }
        div[data-testid="stButton"] > button,
        div[data-testid="stFormSubmitButton"] > button { min-height: 48px !important; width: 100%; }

        /* Abas rolam na horizontal, fixas no topo */
        [data-testid="stTabs"] [role="tablist"] {
            position: sticky; top: 0; z-index: 50;
            backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
            background: rgba(10, 14, 23, 0.85);
        }

        /* Tabelas rolam sem quebrar o layout */
        [data-testid="stDataFrame"], [data-testid="stTable"] { overflow-x: auto; border-radius: 14px; }

        /* Safe-area (iPhone com notch) */
        [data-testid="stAppViewContainer"] main .block-container {
            padding-bottom: calc(5rem + env(safe-area-inset-bottom)) !important;
        }
    }

    @media (max-width: 420px) {
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }
    }
    """
)

# ==========================================
# FUNÇÕES DE BANCO DE DADOS (JSON / FIRESTORE)
# ==========================================
@st.cache_resource(show_spinner=False)
def cliente_firestore():
    try:
        from google.cloud import firestore
        # 1. Verifica se credenciais foram fornecidas via st.secrets (Streamlit Cloud)
        try:
            if hasattr(st, "secrets"):
                from google.oauth2 import service_account
                candidatos_secrets = []
                for chave in ["gcp_service_account", "firebase", "firestore", "google_credentials"]:
                    if chave in st.secrets:
                        candidatos_secrets.append(dict(st.secrets[chave]))
                if "project_id" in st.secrets and "private_key" in st.secrets:
                    candidatos_secrets.append(dict(st.secrets))
                for bruta in candidatos_secrets:
                    try:
                        info = {k: v for k, v in bruta.items() if isinstance(v, str)}
                        if "type" not in info:
                            info["type"] = "service_account"
                        if "private_key" in info:
                            info["private_key"] = info["private_key"].replace("\\n", "\n")
                        creds = service_account.Credentials.from_service_account_info(info)
                        return firestore.Client(credentials=creds, project=info.get("project_id", "kwborachoque-313e3"))
                    except Exception:
                        continue
        except Exception:
            pass
        # 2. Verifica se arquivo local de credenciais do Firebase existe
        caminho_cred = os.path.join(DIRETORIO_APP, "kwborachoque-313e3-firebase-adminsdk-fbsvc-8b0fbe3d51.json")
        if os.path.isfile(caminho_cred):
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_file(caminho_cred)
            return firestore.Client(credentials=creds, project="kwborachoque-313e3")
        # 3. Tentativa padrão de client do ambiente
        return firestore.Client(project="kwborachoque-313e3")
    except Exception:
        return None

def carregar_dados(usuario):
    contas_alvo = ["leo", "william", "wilian"] if eh_administrador(usuario) else [usuario]
    if usuario and usuario not in contas_alvo:
        contas_alvo.append(usuario)

    if USAR_FIRESTORE:
        cli = cliente_firestore()
        if cli is not None:
            try:
                alunos = {}
                for conta_ref in contas_alvo:
                    colecao = cli.collection("contas").document(conta_ref).collection("alunos")
                    for documento in colecao.stream():
                        registro = documento.to_dict() or {}
                        nome = registro.pop("nome", documento.id)
                        chave_existente = next(
                            (k for k in alunos if str(k).strip().casefold() == str(nome).strip().casefold()),
                            None,
                        )
                        if chave_existente is None:
                            alunos[nome] = registro
                        else:
                            atual = alunos[chave_existente]
                            if not atual.get("treinos") and registro.get("treinos"):
                                alunos[chave_existente] = registro
                if alunos:
                    # Garante que os documentos pais de ambos os admins (leo e william) existam e fiquem sincronizados na nuvem
                    if eh_administrador(usuario):
                        for adm_c in ["leo", "william"]:
                            try:
                                doc_adm = cli.collection("contas").document(adm_c)
                                doc_adm.set(
                                    {"admin": adm_c, "tipo": "admin", "ativo": True, "total_alunos": len(alunos)},
                                    merge=True,
                                )
                            except Exception:
                                pass
                    # Atualiza o cache local também para manter ambos sincronizados
                    try:
                        if os.path.exists(ARQUIVO_DADOS):
                            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                                d_local = json.load(f)
                        else:
                            d_local = {"versao": 2, "contas": {}}
                        if "contas" not in d_local or not isinstance(d_local["contas"], dict):
                            d_local["contas"] = {}
                        for conta_ref in ["leo", "william"]:
                            d_local["contas"][conta_ref] = alunos
                        d_local["contas"].pop("wilian", None)
                        d_local["contas"].pop("willian", None)
                        salvar_arquivo_dados(d_local)
                    except Exception:
                        pass
                    return alunos
            except Exception:
                pass

    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception:
            dados = {"versao": 2, "contas": {}}
    else:
        dados = {"versao": 2, "contas": {}}

    if dados.get("versao") == 2 and isinstance(dados.get("contas"), dict):
        local = {}
        for conta_ref in contas_alvo:
            for nome, dados_aluno in dados["contas"].get(conta_ref, {}).items():
                chave_existente = next(
                    (k for k in local if str(k).strip().casefold() == str(nome).strip().casefold()),
                    None,
                )
                if chave_existente is None:
                    local[nome] = dados_aluno
                elif not local[chave_existente].get("treinos") and dados_aluno.get("treinos"):
                    local[chave_existente] = dados_aluno
        # Nuvem vazia mas local com dados (ex.: treinos dos admins): envia para a nuvem
        if local and USAR_FIRESTORE:
            cli = cliente_firestore()
            if cli is not None:
                try:
                    for conta_ref in contas_alvo:
                        doc_adm = cli.collection("contas").document(conta_ref)
                        doc_adm.set(
                            {"admin": conta_ref, "tipo": "admin" if eh_administrador(conta_ref) else "usuario", "ativo": True},
                            merge=True,
                        )
                        colecao = doc_adm.collection("alunos")
                        for nome, dados_aluno in local.items():
                            identificador = hashlib.sha256(nome.encode("utf-8")).hexdigest()
                            colecao.document(identificador).set({"nome": nome, **dados_aluno})
                except Exception:
                    pass
        return local

    usuarios = carregar_usuarios()
    contas = {}
    if usuarios:
        primeiro_usuario = next(iter(usuarios))
        contas[primeiro_usuario] = dados
    try:
        salvar_arquivo_dados({"versao": 2, "contas": contas})
    except Exception:
        pass
    return contas.get(usuario, {})

def salvar_arquivo_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def salvar_usuarios(usuarios):
    # REGRA ESTREITA: Somente Leo e William são administradores. Todos os outros são alunos/usuários.
    for u_nome, u_reg in usuarios.items():
        if eh_administrador(u_nome):
            u_reg["tipo"] = "admin"
        else:
            u_reg["tipo"] = "usuario"

    # PERSISTÊNCIA DUPLA: Salva no Firestore (Nuvem) E salva localmente no usuarios.json
    if USAR_FIRESTORE:
        cli = cliente_firestore()
        if cli is not None:
            try:
                colecao = cli.collection("usuarios")
                for nome, registro in usuarios.items():
                    colecao.document(nome).set(registro)
                    if eh_administrador(nome):
                        cli.collection("contas").document(nome).set(
                            {"admin": nome, "tipo": "admin", "ativo": True},
                            merge=True,
                        )
            except Exception:
                pass

    try:
        with open(ARQUIVO_USUARIOS, "w", encoding="utf-8") as arquivo:
            json.dump(usuarios, arquivo, indent=4, ensure_ascii=False)
    except Exception:
        pass

def remover_usuario(nome_usuario):
    """Remove a conta do login (Firestore + local). Admins nunca são removidos."""
    if eh_administrador(nome_usuario):
        return False
    if USAR_FIRESTORE:
        cli = cliente_firestore()
        if cli is not None:
            try:
                cli.collection("usuarios").document(nome_usuario).delete()
            except Exception:
                pass
    try:
        if os.path.exists(ARQUIVO_USUARIOS):
            with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as f:
                locais = json.load(f)
            if nome_usuario in locais:
                locais.pop(nome_usuario)
                with open(ARQUIVO_USUARIOS, "w", encoding="utf-8") as f:
                    json.dump(locais, f, indent=4, ensure_ascii=False)
    except Exception:
        pass
    return True

def excluir_aluno_total(conta_dados, nome_aluno, db_sessao):
    """Apaga a ficha (nuvem + local + sessão) e os logins do aluno. Retorna lista de erros."""
    erros = []
    alvo = nome_aluno.strip().casefold()

    # 1. Sessão
    for chave in [k for k in list(db_sessao.keys()) if str(k).strip().casefold() == alvo]:
        db_sessao.pop(chave, None)

    # 2. Arquivo local de treinos
    try:
        if os.path.exists(ARQUIVO_DADOS):
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
            contas = dados.get("contas", {}) if isinstance(dados, dict) else {}
            for conta, alunos in contas.items():
                if isinstance(alunos, dict):
                    for chave in [k for k in list(alunos.keys()) if str(k).strip().casefold() == alvo]:
                        alunos.pop(chave, None)
            salvar_arquivo_dados(dados)
    except Exception as e:
        erros.append(f"arquivo local de treinos: {e}")

    # 3. Firestore: fichas
    contas_login = []
    if USAR_FIRESTORE:
        cli = cliente_firestore()
        if cli is not None:
            try:
                for conta_doc in cli.collection("contas").stream():
                    colecao = cli.collection("contas").document(conta_doc.id).collection("alunos")
                    for doc in colecao.stream():
                        reg = doc.to_dict() or {}
                        if str(reg.get("nome", doc.id)).strip().casefold() == alvo:
                            doc.reference.delete()
                for conta in ADMINS_AUTORIZADOS | {conta_dados}:
                    colecao = cli.collection("contas").document(conta).collection("alunos")
                    for doc in colecao.stream():
                        reg = doc.to_dict() or {}
                        if str(reg.get("nome", doc.id)).strip().casefold() == alvo:
                            doc.reference.delete()
            except Exception as e:
                erros.append(f"nuvem (treinos): {e}")

    # 4. Logins vinculados (nuvem + local)
    try:
        usuarios_atuais = carregar_usuarios()
        for u_nome, u_reg in usuarios_atuais.items():
            if eh_administrador(u_nome):
                continue
            if str(u_reg.get("aluno", "")).strip().casefold() == alvo or u_nome.strip().casefold() == alvo:
                contas_login.append(u_nome)
        for u_nome in contas_login:
            remover_usuario(u_nome)
    except Exception as e:
        erros.append(f"logins: {e}")
    return erros, contas_login

def salvar_dados(dados_usuario, usuario):
    admin_auth = st.session_state.get("usuario_autenticado", "")
    if not eh_administrador(admin_auth):
        raise PermissionError("Acesso negado: Somente os administradores (Leo e William) podem alterar treinos.")

    contas_alvo = ["leo", "william"] if eh_administrador(usuario) else [usuario]
    if usuario and usuario not in contas_alvo and usuario not in {"wilian", "willian"}:
        contas_alvo.append(usuario)

    # PERSISTÊNCIA DUPLA: Salva no Firestore (Nuvem) E salva localmente no dados_treinos.json
    if USAR_FIRESTORE:
        cli = cliente_firestore()
        if cli is not None:
            try:
                for conta_ref in contas_alvo:
                    doc_conta = cli.collection("contas").document(conta_ref)
                    doc_conta.set(
                        {
                            "admin": conta_ref,
                            "tipo": "admin" if eh_administrador(conta_ref) else "usuario",
                            "ativo": True,
                            "total_alunos": len(dados_usuario),
                        },
                        merge=True,
                    )
                    colecao = doc_conta.collection("alunos")
                    documentos_existentes = {
                        documento.id: documento
                        for documento in colecao.stream()
                    }
                    nomes_salvos = set()
                    for nome, dados_aluno in dados_usuario.items():
                        identificador = hashlib.sha256(nome.encode("utf-8")).hexdigest()
                        colecao.document(identificador).set({"nome": nome, **dados_aluno})
                        nomes_salvos.add(identificador)
                    for identificador, documento in documentos_existentes.items():
                        if identificador not in nomes_salvos:
                            documento.reference.delete()
            except Exception:
                pass

    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception:
            dados = {"versao": 2, "contas": {}}
    else:
        dados = {"versao": 2, "contas": {}}

    if dados.get("versao") != 2 or not isinstance(dados.get("contas"), dict):
        contas = {adm: {} for adm in ["leo", "william"]}
        dados = {"versao": 2, "contas": contas}

    for conta_ref in contas_alvo:
        dados["contas"][conta_ref] = dados_usuario
    dados["contas"].pop("wilian", None)
    dados["contas"].pop("willian", None)
    try:
        salvar_arquivo_dados(dados)
    except Exception:
        pass

def carregar_usuarios():
    # 1. Lê o arquivo local
    if os.path.exists(ARQUIVO_USUARIOS):
        try:
            with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as arquivo:
                usuarios = json.load(arquivo)
        except Exception:
            usuarios = {}
    else:
        usuarios = {}
    if not isinstance(usuarios, dict):
        usuarios = {}

    # 2. Mescla com o Firestore (nuvem). Registros da nuvem têm prioridade, mas
    #    usuários que só existem localmente (ex.: admins) NÃO são perdidos —
    #    eles são enviados para a nuvem para que "não existe" não volte a ocorrer.
    if USAR_FIRESTORE:
        cli = cliente_firestore()
        if cli is not None:
            try:
                nuvem = {
                    documento.id: documento.to_dict()
                    for documento in cli.collection("usuarios").stream()
                }
                apenas_locais = [n for n in usuarios if n not in nuvem and n not in {"wilian", "willian"}]
                for u_nome, u_reg in nuvem.items():
                    if isinstance(u_reg, dict) and u_reg.get("hash") and u_reg.get("salt"):
                        usuarios[u_nome] = u_reg
                for u_nome in apenas_locais:
                    try:
                        cli.collection("usuarios").document(u_nome).set(usuarios[u_nome])
                    except Exception:
                        pass
            except Exception:
                pass

    if not usuarios:
        # Fallback inicial seguro para garantir que a aplicação nunca abra sem login no Streamlit Cloud
        usuarios = {
            "leo": {
                "salt": "6016dac021652a820a05d5fe89d3c36f",
                "hash": "8ad3c1f5fb334d592435e0bdcfad76836e9860b948683e8d1bac5a4414742d47",
                "tipo": "admin",
                "perfil": {
                    "peso": 94.0,
                    "peso_kg": 94.0,
                    "altura": 180.5,
                    "altura_cm": 180.5,
                    "idade": 37,
                    "sexo": "Masculino"
                }
            },
            "william": {
                "salt": "4314dae8bc86258615cbd9885d5a8f1a",
                "hash": "16dd48325f790d2047a3c46fe234fa035f0391b82413b20869a69cb502f975d0",
                "tipo": "admin"
            }
        }
        try:
            salvar_usuarios(usuarios)
        except Exception:
            pass

    # Migra grafias antigas ("wilian" / "willian") para "william"
    alterado = False
    for grafia_antiga in ("wilian", "willian"):
        if grafia_antiga in usuarios:
            reg_antigo = usuarios.pop(grafia_antiga)
            if "william" not in usuarios and isinstance(reg_antigo, dict):
                usuarios["william"] = reg_antigo
            if USAR_FIRESTORE:
                cli = cliente_firestore()
                if cli is not None:
                    try:
                        cli.collection("usuarios").document(grafia_antiga).delete()
                    except Exception:
                        pass
            alterado = True

    # REGRA: SOMENTE LEO E WILLIAM SÃO ADMINS. TODOS OS OUTROS SÃO USUÁRIOS/ALUNOS.
    for u_nome, u_reg in usuarios.items():
        if eh_administrador(u_nome):
            if u_reg.get("tipo") != "admin":
                u_reg["tipo"] = "admin"
                alterado = True
        else:
            if u_reg.get("tipo") != "usuario":
                u_reg["tipo"] = "usuario"
                alterado = True

    # Garante que leo e william sempre existam no sistema com credenciais válidas e tipo "admin"
    if "leo" not in usuarios:
        usuarios["leo"] = {
            "salt": "6016dac021652a820a05d5fe89d3c36f",
            "hash": "8ad3c1f5fb334d592435e0bdcfad76836e9860b948683e8d1bac5a4414742d47",
            "tipo": "admin"
        }
        alterado = True
    if "william" not in usuarios or usuarios["william"].get("salt") == "9f2b8c7e1d4a5b6c3e2f1a0b9c8d7e6f":
        perfil_william = usuarios.get("william", {}).get("perfil") if isinstance(usuarios.get("william"), dict) else None
        usuarios["william"] = {
            "salt": "4314dae8bc86258615cbd9885d5a8f1a",
            "hash": "16dd48325f790d2047a3c46fe234fa035f0391b82413b20869a69cb502f975d0",
            "tipo": "admin"
        }
        if perfil_william:
            usuarios["william"]["perfil"] = perfil_william
        alterado = True

    if alterado:
        try:
            salvar_usuarios(usuarios)
        except Exception:
            pass
    return usuarios

def gerar_hash_senha(senha, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt.encode("ascii"), 310_000
    ).hex()

# ==========================================
# GESTÃO DE SESSÃO PERSISTENTE (ANTI-DESCONEXÃO NO F5)
# ==========================================
SEGREDO_SESSAO = "kn_alta_performance_session_secret_key_v1"

def gerar_token_sessao(usuario, registro):
    dados = f"{usuario}:{registro.get('hash', '')}"
    assinatura = hmac.new(
        SEGREDO_SESSAO.encode("utf-8"),
        dados.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    payload = f"{usuario}:{assinatura}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")

def validar_token_sessao(token, usuarios_dict):
    if not token or not isinstance(token, str):
        return None
    try:
        conteudo = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        if ":" not in conteudo:
            return None
        usuario, assinatura = conteudo.split(":", 1)
        registro = usuarios_dict.get(usuario)
        if not registro:
            return None
        dados = f"{usuario}:{registro.get('hash', '')}"
        esperada = hmac.new(
            SEGREDO_SESSAO.encode("utf-8"),
            dados.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        if hmac.compare_digest(esperada, assinatura):
            return usuario
    except Exception:
        return None
    return None

def definir_sessao_url(token):
    try:
        if hasattr(st, "query_params"):
            st.query_params["session"] = token
        elif hasattr(st, "experimental_set_query_params"):
            st.experimental_set_query_params(session=token)
    except Exception:
        pass

def obter_sessao_url():
    try:
        if hasattr(st, "query_params"):
            return st.query_params.get("session") or st.query_params.get("auth")
        elif hasattr(st, "experimental_get_query_params"):
            params = st.experimental_get_query_params()
            res = params.get("session") or params.get("auth")
            if res and isinstance(res, list):
                return res[0]
            return res
    except Exception:
        pass
    return None

def limpar_sessao_url():
    try:
        if hasattr(st, "query_params"):
            st.query_params.clear()
        elif hasattr(st, "experimental_set_query_params"):
            st.experimental_set_query_params()
    except Exception:
        pass

def normalizar_url_video(url):
    if not url or not isinstance(url, str):
        return ""
    url = url.strip()
    if url.startswith("arquivo_local:") or url.startswith("data:video/"):
        return url
    if "youtube.com/shorts/" in url:
        url = url.replace("youtube.com/shorts/", "youtube.com/watch?v=")
    elif "youtu.be/" in url:
        try:
            id_vid = url.split("youtu.be/")[1].split("?")[0].split("/")[0]
            url = f"https://www.youtube.com/watch?v={id_vid}"
        except Exception:
            pass
    elif "m.youtube.com" in url:
        url = url.replace("m.youtube.com", "www.youtube.com")
    return url

# ==========================================
# GESTÃO DE VÍDEOS E GRAVAÇÃO (EXCLUSIVO ADMIN)
# ==========================================
def carregar_catalogo_videos():
    catalogo = {}
    if os.path.exists(ARQUIVO_CATALOGO_VIDEOS):
        try:
            with open(ARQUIVO_CATALOGO_VIDEOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, dict):
                catalogo = dados
        except Exception:
            catalogo = {}

    if USAR_FIRESTORE:
        cli = cliente_firestore()
        if cli is not None:
            try:
                for doc in cli.collection("catalogo_videos").stream():
                    reg = doc.to_dict() or {}
                    chave = reg.get("chave") or f"{reg.get('modalidade', '')}::{reg.get('exercicio', '')}"
                    if chave and "::" in chave:
                        catalogo[chave] = {
                            "modalidade": reg.get("modalidade", chave.split("::", 1)[0]),
                            "exercicio": reg.get("exercicio", chave.split("::", 1)[1]),
                            "url_video": reg.get("url_video", ""),
                            "observacoes": reg.get("observacoes", ""),
                        }
                if catalogo:
                    try:
                        with open(ARQUIVO_CATALOGO_VIDEOS, "w", encoding="utf-8") as f:
                            json.dump(catalogo, f, indent=4, ensure_ascii=False)
                    except Exception:
                        pass
            except Exception:
                pass
    return catalogo

def salvar_catalogo_videos(catalogo):
    admin_auth = st.session_state.get("usuario_autenticado", "")
    if not eh_administrador(admin_auth):
        raise PermissionError("Acesso negado: Somente os administradores podem gerenciar vídeos.")

    try:
        with open(ARQUIVO_CATALOGO_VIDEOS, "w", encoding="utf-8") as f:
            json.dump(catalogo, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

    if USAR_FIRESTORE:
        cli = cliente_firestore()
        if cli is not None:
            try:
                colecao = cli.collection("catalogo_videos")
                existentes = {d.id: d for d in colecao.stream()}
                salvos = set()
                for chave, info in catalogo.items():
                    if not isinstance(info, dict):
                        continue
                    doc_id = hashlib.sha256(chave.encode("utf-8")).hexdigest()
                    colecao.document(doc_id).set({"chave": chave, **info})
                    salvos.add(doc_id)
                for doc_id, doc_ref in existentes.items():
                    if doc_id not in salvos:
                        doc_ref.reference.delete()
            except Exception:
                pass
    st.session_state["catalogo_videos"] = catalogo

def obter_catalogo_sessao():
    if "catalogo_videos" not in st.session_state or not isinstance(st.session_state.get("catalogo_videos"), dict):
        st.session_state["catalogo_videos"] = carregar_catalogo_videos()
    return st.session_state["catalogo_videos"]

def obter_exercicios_modalidade(modalidade, catalogo=None):
    if catalogo is None:
        catalogo = obter_catalogo_sessao()
    base = list(MODALIDADES_EXERCICIOS.get(modalidade, []))
    vistos = {e.strip().casefold() for e in base}
    for chave, info in catalogo.items():
        if isinstance(info, dict) and info.get("modalidade") == modalidade:
            ex = str(info.get("exercicio", "")).strip()
            if ex and ex.casefold() not in vistos:
                base.append(ex)
                vistos.add(ex.casefold())
    if "db" in st.session_state and isinstance(st.session_state.db, dict):
        for dados_al in st.session_state.db.values():
            if isinstance(dados_al, dict) and dados_al.get("modalidade") == modalidade:
                for t in dados_al.get("treinos", []):
                    ex = str(t.get("exercicio", "")).strip()
                    if ex and ex.casefold() not in vistos:
                        base.append(ex)
                        vistos.add(ex.casefold())
    return base

def obter_video_catalogo(modalidade, exercicio, catalogo=None):
    if not exercicio:
        return ""
    if catalogo is None:
        catalogo = obter_catalogo_sessao()
    chave_exata = f"{modalidade}::{exercicio}"
    if chave_exata in catalogo and isinstance(catalogo[chave_exata], dict):
        vid = str(catalogo[chave_exata].get("url_video", "")).strip()
        if vid:
            return vid
    mod_cf = str(modalidade or "").strip().casefold()
    ex_cf = str(exercicio).strip().casefold()
    for info in catalogo.values():
        if isinstance(info, dict):
            if str(info.get("modalidade", "")).strip().casefold() == mod_cf and str(info.get("exercicio", "")).strip().casefold() == ex_cf:
                vid = str(info.get("url_video", "")).strip()
                if vid:
                    return vid
    for info in catalogo.values():
        if isinstance(info, dict) and str(info.get("exercicio", "")).strip().casefold() == ex_cf:
            vid = str(info.get("url_video", "")).strip()
            if vid:
                return vid
    return ""

def salvar_arquivo_video_upload(arquivo_upload, prefixo="exercicio"):
    admin_auth = st.session_state.get("usuario_autenticado", "")
    if not eh_administrador(admin_auth):
        raise PermissionError("Somente administradores podem enviar ou gravar vídeos.")

    os.makedirs(DIRETORIO_VIDEOS, exist_ok=True)
    conteudo = arquivo_upload.getvalue()
    if not conteudo:
        raise ValueError("O arquivo de vídeo está vazio.")

    nome_orig = getattr(arquivo_upload, "name", "video.mp4") or "video.mp4"
    _, ext = os.path.splitext(nome_orig)
    ext = ext.lower() if ext else ".mp4"
    if ext not in {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v", ".3gp"}:
        ext = ".mp4"

    slug = re.sub(r"[^a-z0-9]+", "_", str(prefixo).lower()).strip("_")[:30] or "exercicio"
    hash_curto = hashlib.sha256(conteudo).hexdigest()[:12]
    nome_final = f"vid_{slug}_{hash_curto}{ext}"
    caminho_completo = os.path.join(DIRETORIO_VIDEOS, nome_final)

    with open(caminho_completo, "wb") as f:
        f.write(conteudo)

    # Sincroniza em partes no Firestore se ativo (para funcionar também na nuvem até ~20MB)
    if USAR_FIRESTORE and len(conteudo) <= 20 * 1024 * 1024:
        cli = cliente_firestore()
        if cli is not None:
            try:
                b64_total = base64.b64encode(conteudo).decode("ascii")
                tam_bloco = 700_000
                partes = [b64_total[i:i + tam_bloco] for i in range(0, len(b64_total), tam_bloco)]
                doc_vid = cli.collection("arquivos_videos").document(nome_final)
                doc_vid.set({
                    "nome_arquivo": nome_final,
                    "tamanho_bytes": len(conteudo),
                    "total_partes": len(partes),
                    "extensao": ext,
                    "autor": admin_auth,
                })
                col_partes = doc_vid.collection("partes")
                for idx_p, texto_parte in enumerate(partes):
                    col_partes.document(f"{idx_p:04d}").set({"indice": idx_p, "dados": texto_parte})
            except Exception:
                pass

    return f"arquivo_local:{nome_final}"

def resolver_midia_video(url_ou_ref):
    if not url_ou_ref or not isinstance(url_ou_ref, str):
        return None
    ref = url_ou_ref.strip()
    if not ref:
        return None

    if ref.startswith("arquivo_local:"):
        nome_arquivo = ref.split("arquivo_local:", 1)[1].strip()
        nome_seguro = os.path.basename(nome_arquivo)
        caminho_local = os.path.join(DIRETORIO_VIDEOS, nome_seguro)
        if os.path.isfile(caminho_local):
            return caminho_local
        if USAR_FIRESTORE:
            cli = cliente_firestore()
            if cli is not None:
                try:
                    doc_vid = cli.collection("arquivos_videos").document(nome_seguro)
                    docs_partes = list(doc_vid.collection("partes").stream())
                    if docs_partes:
                        docs_partes.sort(key=lambda d: (d.to_dict() or {}).get("indice", 0))
                        b64_unido = "".join((d.to_dict() or {}).get("dados", "") for d in docs_partes)
                        if b64_unido:
                            os.makedirs(DIRETORIO_VIDEOS, exist_ok=True)
                            with open(caminho_local, "wb") as f:
                                f.write(base64.b64decode(b64_unido))
                            return caminho_local
                except Exception:
                    pass
        return None

    if ref.startswith("data:video/"):
        try:
            raw_b64 = ref.split("base64,", 1)[1]
            return BytesIO(base64.b64decode(raw_b64))
        except Exception:
            return None

    if os.path.isfile(ref):
        return ref

    return normalizar_url_video(ref)

def exibir_player_video(url_ou_ref):
    midia = resolver_midia_video(url_ou_ref)
    if midia is None:
        st.warning("Vídeo não encontrado ou link inválido.")
        return False
    try:
        st.video(midia)
        return True
    except Exception:
        st.warning("Não foi possível reproduzir o vídeo. Verifique o arquivo ou link informado.")
        return False

def renderizar_gravador_camera_html(chave_unica, nome_exercicio="exercicio"):
    """Renderiza gravador de vídeo via câmera (webcam / celular frontal e traseira) integrado ao uploader."""
    slug_ex = re.sub(r"[^a-z0-9]+", "_", str(nome_exercicio).lower()).strip("_")[:24] or "exercicio"
    chave_container = f"box_up_vid_{chave_unica}"
    html_gravador = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        * {{ box-sizing: border-box; font-family: 'Plus Jakarta Sans', -apple-system, sans-serif; }}
        body {{
            margin: 0; padding: 12px;
            background:
                linear-gradient(145deg, rgba(17, 24, 39, 0.80) 0%, rgba(11, 17, 32, 0.86) 100%),
                url('data:image/jpeg;base64,{LOGO_BASE64 or ""}') center center / contain no-repeat;
            background-color: #0b1120;
            color: #f8fafc;
            border: 1.5px solid rgba(245, 196, 0, 0.35);
            border-radius: 16px;
        }}
        .top-bar {{
            display: flex; align-items: center; justify-content: space-between;
            gap: 8px; flex-wrap: wrap; margin-bottom: 10px;
        }}
        .badge {{
            background: rgba(245, 196, 0, 0.16); color: #f5c400;
            border: 1px solid rgba(245, 196, 0, 0.4);
            padding: 4px 12px; border-radius: 999px; font-weight: 800; font-size: 0.78rem;
        }}
        .timer {{
            background: rgba(239, 68, 68, 0.18); color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.4);
            padding: 4px 12px; border-radius: 999px; font-weight: 800; font-size: 0.82rem;
            display: none;
        }}
        .timer.active {{ display: inline-block; animation: pulse 1.2s infinite; }}
        @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.45; }} 100% {{ opacity: 1; }} }}
        select {{
            background: #ffffff; color: #000000; font-weight: 700;
            border: 1px solid #cbd5e1; border-radius: 10px; padding: 6px 10px; font-size: 0.82rem;
        }}
        .video-box {{
            width: 100%; height: 240px; background: #050811;
            border: 1px dashed rgba(255,255,255,0.18); border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            overflow: hidden; position: relative; margin-bottom: 10px;
        }}
        video {{ width: 100%; height: 100%; object-fit: cover; border-radius: 12px; }}
        .placeholder {{ text-align: center; color: #94a3b8; font-size: 0.85rem; padding: 16px; }}
        .btn-row {{ display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }}
        button {{
            border: none; border-radius: 11px; padding: 9px 14px;
            font-weight: 800; font-size: 0.84rem; cursor: pointer;
            transition: transform 0.12s ease, opacity 0.2s ease;
        }}
        button:active {{ transform: scale(0.97); }}
        button:disabled {{ opacity: 0.4; cursor: not-allowed; }}
        .btn-cam {{ background: #38bdf8; color: #082f49; }}
        .btn-rec {{ background: #ef4444; color: #ffffff; }}
        .btn-stop {{ background: #f59e0b; color: #111827; }}
        .btn-use {{ background: linear-gradient(135deg, #f5c400 0%, #eab308 100%); color: #111827; }}
        .btn-dl {{ background: rgba(255,255,255,0.1); color: #f8fafc; border: 1px solid rgba(255,255,255,0.2); }}
        .status {{ text-align: center; font-size: 0.8rem; color: #cbd5e1; margin-top: 8px; min-height: 18px; }}
    </style>
    </head>
    <body>
        <div class="top-bar">
            <span class="badge">🎥 GRAVADOR DE VÍDEO AO VIVO</span>
            <select id="camMode" title="Escolher Câmera">
                <option value="environment">📱 Câmera Traseira / Principal</option>
                <option value="user">🤳 Câmera Frontal / Webcam</option>
            </select>
            <span id="recTimer" class="timer">🔴 GRAVANDO 00:00</span>
        </div>

        <div class="video-box">
            <div id="placeholderMsg" class="placeholder">
                🎬 Clique em <b>"1. Ligar Câmera"</b> abaixo para filmar o exercício direto pelo navegador.
            </div>
            <video id="liveVideo" autoplay muted playsinline style="display:none;"></video>
            <video id="recordedVideo" controls playsinline style="display:none;"></video>
        </div>

        <div class="btn-row">
            <button id="btnStartCam" class="btn-cam" onclick="startCamera()">📷 1. Ligar Câmera</button>
            <button id="btnStartRec" class="btn-rec" onclick="startRecording()" disabled>🔴 2. Gravar</button>
            <button id="btnStopRec" class="btn-stop" onclick="stopRecording()" disabled>⏹️ 3. Parar</button>
            <button id="btnUseVid" class="btn-use" onclick="sendToUploader()" style="display:none;">✅ 4. Anexar Vídeo Gravado</button>
            <button id="btnDownload" class="btn-dl" onclick="downloadRecorded()" style="display:none;">⬇️ Baixar Vídeo</button>
        </div>
        <div id="statusText" class="status">Pronto para gravar exercício.</div>

        <script>
        let mediaStream = null;
        let mediaRecorder = null;
        let recordedChunks = [];
        let recordedBlob = null;
        let recordedMime = 'video/webm';
        let recordedExt = 'webm';
        let timerInterval = null;
        let secondsElapsed = 0;

        const liveVideo = document.getElementById('liveVideo');
        const recordedVideo = document.getElementById('recordedVideo');
        const placeholderMsg = document.getElementById('placeholderMsg');
        const btnStartCam = document.getElementById('btnStartCam');
        const btnStartRec = document.getElementById('btnStartRec');
        const btnStopRec = document.getElementById('btnStopRec');
        const btnUseVid = document.getElementById('btnUseVid');
        const btnDownload = document.getElementById('btnDownload');
        const recTimer = document.getElementById('recTimer');
        const statusText = document.getElementById('statusText');
        const camMode = document.getElementById('camMode');

        function formatTime(sec) {{
            const m = String(Math.floor(sec / 60)).padStart(2, '0');
            const s = String(sec % 60).padStart(2, '0');
            return m + ':' + s;
        }}

        async function startCamera() {{
            try {{
                if (mediaStream) {{
                    mediaStream.getTracks().forEach(t => t.stop());
                }}
                const facing = camMode.value;
                statusText.innerText = 'Solicitando permissão da câmera...';
                try {{
                    mediaStream = await navigator.mediaDevices.getUserMedia({{
                        video: {{ facingMode: {{ ideal: facing }}, width: {{ ideal: 1280 }}, height: {{ ideal: 720 }} }},
                        audio: true
                    }});
                }} catch (errAudio) {{
                    mediaStream = await navigator.mediaDevices.getUserMedia({{
                        video: true,
                        audio: false
                    }});
                }}
                placeholderMsg.style.display = 'none';
                recordedVideo.style.display = 'none';
                recordedVideo.src = '';
                liveVideo.style.display = 'block';
                liveVideo.srcObject = mediaStream;
                btnStartRec.disabled = false;
                btnStopRec.disabled = true;
                btnUseVid.style.display = 'none';
                btnDownload.style.display = 'none';
                statusText.innerText = 'Câmera ativa! Clique em "2. Gravar" para iniciar a filmagem.';
            }} catch (e) {{
                statusText.innerText = '⚠️ Não foi possível acessar a câmera no navegador. Use o botão "Browse files" abaixo para gravar pela câmera nativa do celular ou enviar arquivo.';
            }}
        }}

        function startRecording() {{
            if (!mediaStream) return;
            recordedChunks = [];
            const mimeCandidates = [
                'video/mp4',
                'video/webm;codecs=vp9,opus',
                'video/webm;codecs=vp8,opus',
                'video/webm'
            ];
            recordedMime = 'video/webm';
            for (const m of mimeCandidates) {{
                if (window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(m)) {{
                    recordedMime = m;
                    break;
                }}
            }}
            recordedExt = recordedMime.includes('mp4') ? 'mp4' : 'webm';
            try {{
                mediaRecorder = new MediaRecorder(mediaStream, {{ mimeType: recordedMime }});
            }} catch (e) {{
                mediaRecorder = new MediaRecorder(mediaStream);
            }}
            mediaRecorder.ondataavailable = (ev) => {{
                if (ev.data && ev.data.size > 0) recordedChunks.push(ev.data);
            }};
            mediaRecorder.onstop = () => {{
                recordedBlob = new Blob(recordedChunks, {{ type: recordedMime }});
                const url = URL.createObjectURL(recordedBlob);
                liveVideo.style.display = 'none';
                recordedVideo.style.display = 'block';
                recordedVideo.src = url;
                btnUseVid.style.display = 'inline-block';
                btnDownload.style.display = 'inline-block';
                statusText.innerHTML = '✅ Vídeo gravado! Clique em <b>"4. Anexar Vídeo Gravado"</b> e depois em <b>"Salvar Vídeo"</b>.';
                if (mediaStream) {{
                    mediaStream.getTracks().forEach(t => t.stop());
                }}
            }};
            mediaRecorder.start(250);
            secondsElapsed = 0;
            recTimer.innerText = '🔴 GRAVANDO 00:00';
            recTimer.classList.add('active');
            timerInterval = setInterval(() => {{
                secondsElapsed++;
                recTimer.innerText = '🔴 GRAVANDO ' + formatTime(secondsElapsed);
            }}, 1000);
            btnStartRec.disabled = true;
            btnStopRec.disabled = false;
            statusText.innerText = 'Gravando exercício... Clique em "3. Parar" quando terminar.';
        }}

        function stopRecording() {{
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
                mediaRecorder.stop();
            }}
            if (timerInterval) clearInterval(timerInterval);
            recTimer.classList.remove('active');
            btnStopRec.disabled = true;
            btnStartRec.disabled = true;
        }}

        function sendToUploader() {{
            if (!recordedBlob) return;
            const fileName = 'gravacao_{slug_ex}_' + Date.now() + '.' + recordedExt;
            try {{
                const parentDoc = window.parent.document;
                let fileInput = null;
                const container = parentDoc.querySelector('.st-key-{chave_container}');
                if (container) {{
                    fileInput = container.querySelector('input[type="file"]');
                }}
                if (!fileInput) {{
                    const allInputs = parentDoc.querySelectorAll('input[type="file"]');
                    if (allInputs.length > 0) fileInput = allInputs[0];
                }}
                if (fileInput) {{
                    const file = new File([recordedBlob], fileName, {{ type: recordedBlob.type || 'video/webm' }});
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    fileInput.files = dt.files;
                    fileInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    fileInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    statusText.innerHTML = '🎉 <b>Vídeo anexado automaticamente abaixo!</b> Agora clique no botão amarelo <b>"💾 Salvar Vídeo Gravado/Enviado"</b>.';
                    return;
                }}
            }} catch (err) {{
                console.warn(err);
            }}
            downloadRecorded();
            statusText.innerHTML = '⬇️ O vídeo foi baixado no seu aparelho. Selecione-o na caixa abaixo para salvar.';
        }}

        function downloadRecorded() {{
            if (!recordedBlob) return;
            const a = document.createElement('a');
            a.href = URL.createObjectURL(recordedBlob);
            a.download = 'gravacao_{slug_ex}_' + Date.now() + '.' + recordedExt;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }}
        </script>
    </body>
    </html>
    """
    components.html(html_gravador, height=385)

def preparar_foto_perfil(arquivo):
    imagem = Image.open(BytesIO(arquivo.getvalue()))
    imagem = ImageOps.exif_transpose(imagem)

    for dimensao in (512, 384, 256):
        imagem.thumbnail((dimensao, dimensao))
        miniatura = imagem.convert("RGB")
        for qualidade in (85, 75, 65, 55, 45, 35):
            buffer = BytesIO()
            miniatura.save(buffer, format="JPEG", optimize=True, quality=qualidade)
            if buffer.tell() <= TAMANHO_MAXIMO_FOTO_PERFIL:
                base64_str = base64.b64encode(buffer.getvalue()).decode("ascii")
                return f"data:image/jpeg;base64,{base64_str}"

    raise ValueError("A foto é muito grande. Escolha uma imagem menor.")

def calcular_imc(peso_kg, altura_cm):
    if peso_kg is None or altura_cm is None or altura_cm <= 0:
        return None
    altura_m = altura_cm / 100
    return peso_kg / (altura_m * altura_m)

def obter_perfil_atleta(nome_aluno, usuarios_dict):
    perfil = {}
    if nome_aluno in st.session_state.db and isinstance(st.session_state.db[nome_aluno], dict):
        perfil = dict(st.session_state.db[nome_aluno].get("perfil", {}))

    for u_nome, u_reg in usuarios_dict.items():
        if u_reg.get("aluno") == nome_aluno or u_nome.casefold() == nome_aluno.casefold():
            u_perf = u_reg.get("perfil", {})
            for k, v in u_perf.items():
                if v is not None and not perfil.get(k):
                    perfil[k] = v
            break
    return perfil

def notificar_sucesso(mensagem, icone="✅"):
    if hasattr(st, "toast"):
        try:
            st.toast(mensagem, icon=icone)
        except Exception:
            pass

# ==========================================
# GRÁFICOS PERSONALIZADOS (MATPLOTLIB PRO)
# ==========================================
def plot_distribuicao_exercicios(df_treinos):
    contagem = df_treinos['exercicio'].value_counts()
    cores = ['#F5C400', '#38BDF8', '#818CF8', '#34D399', '#FB923C', '#F472B6', '#E879F9']
    
    fig, ax = plt.subplots(figsize=(6, 4.4), facecolor='none')
    ax.set_facecolor('none')
    
    wedges, texts, autotexts = ax.pie(
        contagem,
        labels=contagem.index,
        autopct='%1.0f%%',
        pctdistance=0.76,
        startangle=120,
        colors=cores[:len(contagem)],
        wedgeprops=dict(width=0.42, edgecolor='#0f1523', linewidth=2.5),
        textprops=dict(color='#cbd5e1', fontsize=9.5, fontweight='500')
    )
    for autotext in autotexts:
        autotext.set_color('#ffffff')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(10)
        
    ax.axis('equal')
    plt.tight_layout()
    return fig

def plot_volume_series(df_treinos):
    volume = df_treinos.groupby('exercicio')['series'].sum().sort_values()
    
    fig, ax = plt.subplots(figsize=(6, 4.4), facecolor='none')
    ax.set_facecolor('none')
    
    y_pos = range(len(volume))
    bars = ax.barh(y_pos, volume.values, color='#F5C400', height=0.52, edgecolor='none', zorder=3)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(volume.index, color='#f1f5f9', fontsize=9.5, fontweight='600')
    ax.set_xlabel("Número de Séries", color='#94a3b8', fontsize=9.5, labelpad=8)
    
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
        
    ax.tick_params(colors='#94a3b8', labelsize=9)
    ax.grid(axis='x', color='#ffffff', alpha=0.08, linestyle='--', zorder=0)
    
    ax.bar_label(bars, padding=6, color='#ffffff', fontweight='bold', fontsize=9.5)
    
    if len(volume) > 0:
        max_val = max(volume.values)
        ax.set_xlim(0, max_val * 1.25)
        
    plt.tight_layout()
    return fig

# ==========================================
# TELA DE LOGIN (TODAS AS LETRAS EM PRETO)
# ==========================================
def mostrar_tela_login():
    caminho_foto = obter_caminho_foto_login()
    foto_b64 = carregar_imagem_base64(caminho_foto, (1920, 1920), 85) or FUNDO_LOGO_B64 or LOGO_BASE64 or FUNDO_PADRAO_B64

    if foto_b64:
        estilo_fundo_tela_toda = f"""
        /* FUNDO DA TELA TODA DE LOGIN COM A FOTO EM TELA CHEIA (UNIVERSAL) */
        .stApp::before {{
            content: "" !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            background-color: #05070c !important;
            background-image: 
                linear-gradient(rgba(5, 7, 13, 0.40), rgba(5, 7, 13, 0.70)),
                url('data:image/jpeg;base64,{foto_b64}') !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            background-size: cover !important;
            z-index: 0 !important;
            pointer-events: none !important;
        }}

        html, body, .stApp,
        [data-testid="stApp"],
        [data-testid="stAppViewContainer"],
        .stAppViewContainer {{
            background-color: #05070c !important;
            background-image: 
                linear-gradient(rgba(5, 7, 13, 0.40), rgba(5, 7, 13, 0.70)),
                url('data:image/jpeg;base64,{foto_b64}') !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            background-size: cover !important;
            background-attachment: fixed !important;
            min-height: 100vh !important;
            width: 100vw !important;
        }}
        """
    else:
        estilo_fundo_tela_toda = """
        html, body, .stApp,
        [data-testid="stAppViewContainer"] {
            background-color: #070a10 !important;
            background: radial-gradient(circle at 50% 50%, #172338 0%, #0a0e17 65%, #05070c 100%) !important;
            min-height: 100vh !important;
            width: 100vw !important;
        }
        """

    injetar_css(
        f"""
        /* ESCONDE BARRA LATERAL E CABEÇALHO PARA TELA CHEIA REAL NO LOGIN */
        [data-testid="stSidebar"],
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapseButton"] {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
        }}

        header[data-testid="stHeader"],
        [data-testid="stHeader"] {{
            display: none !important;
            background: transparent !important;
        }}

        {estilo_fundo_tela_toda}

        section.main,
        .main,
        [data-testid="stMain"],
        .stMain,
        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        div[data-testid="stAppViewContainer"] > section,
        div[data-testid="stAppViewContainer"] > div {{
            background: transparent !important;
            background-color: transparent !important;
            position: relative !important;
            z-index: 1 !important;
        }}

        /* Centralização perfeita na tela de login */
        [data-testid="stMainBlockContainer"],
        .block-container {{
            padding-top: calc(50vh - 290px) !important;
            padding-bottom: 2rem !important;
            max-width: 470px !important;
            margin: 0 auto !important;
        }}

        @media (max-height: 700px) {{
            [data-testid="stMainBlockContainer"],
            .block-container {{
                padding-top: 1.5rem !important;
            }}
        }}

        @media (max-width: 768px) {{
            .stApp,
            [data-testid="stAppViewContainer"] {{
                background-attachment: scroll !important;
            }}
            [data-testid="stMainBlockContainer"],
            .block-container {{
                padding-top: 1.2rem !important;
                padding-bottom: 1.8rem !important;
                max-width: 96% !important;
            }}
            .st-key-card_login_box {{
                padding: 1.3rem 1.1rem !important;
                border-radius: 18px !important;
            }}
        }}

        /* Card / Menu de login com a logo do projeto no fundo e letras pretas nítidas */
        .st-key-card_login_box {{
            background-color: #ffffff !important;
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.90)),
                url('data:image/jpeg;base64,{foto_b64 or LOGO_BASE64 or ""}') !important;
            background-position: center center, center center !important;
            background-repeat: no-repeat, no-repeat !important;
            background-size: cover, contain !important;
            border: 2px solid #f5c400 !important;
            border-radius: 24px !important;
            padding: 1.8rem !important;
            box-shadow: 0 25px 60px rgba(0, 0, 0, 0.85), 0 0 35px rgba(245, 196, 0, 0.35) !important;
            backdrop-filter: blur(14px) !important;
            -webkit-backdrop-filter: blur(14px) !important;
        }}

        /* OBRIGA LETRA PRETA EM TODOS OS ELEMENTOS DO MENU INICIAL */
        .st-key-card_login_box h1,
        .st-key-card_login_box h2,
        .st-key-card_login_box h3,
        .st-key-card_login_box p,
        .st-key-card_login_box span,
        .st-key-card_login_box label,
        [data-testid="stAppViewContainer"] main [data-testid="stForm"] label,
        [data-testid="stAppViewContainer"] main [data-testid="stForm"] p,
        [data-testid="stAppViewContainer"] main [data-testid="stWidgetLabel"] p,
        [data-testid="stAppViewContainer"] main [data-testid="stWidgetLabel"] label,
        [data-testid="stAppViewContainer"] main [data-testid="stCaptionContainer"] p,
        [data-testid="stAppViewContainer"] main [data-testid="stTabs"] button[role="tab"] {{
            color: #000000 !important;
            font-weight: 700 !important;
        }}

        /* TEXTO DIGITADO PELO USUÁRIO TOTALMENTE PRETO */
        [data-testid="stAppViewContainer"] main input,
        [data-testid="stAppViewContainer"] main div[data-baseweb="input"] input {{
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            caret-color: #000000 !important;
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            background-color: #f8fafc !important;
        }}

        [data-testid="stAppViewContainer"] main div[data-baseweb="input"] {{
            background-color: #f8fafc !important;
            border: 2px solid #94a3b8 !important;
            border-radius: 12px !important;
        }}

        [data-testid="stAppViewContainer"] main div[data-baseweb="input"]:focus-within {{
            border-color: #f5c400 !important;
            box-shadow: 0 0 0 3px rgba(245, 196, 0, 0.35) !important;
        }}

        /* Sem texto/sombra duplicada atrás do que é digitado (inclui autofill do navegador) */
        [data-testid="stAppViewContainer"] main div[data-baseweb="input"] > div,
        [data-testid="stAppViewContainer"] main div[data-baseweb="base-input"] {{
            background-color: #f8fafc !important;
        }}
        [data-testid="stAppViewContainer"] main input {{
            text-shadow: none !important;
            background-image: none !important;
        }}
        [data-testid="stAppViewContainer"] main input:-webkit-autofill,
        [data-testid="stAppViewContainer"] main input:-webkit-autofill:focus {{
            -webkit-box-shadow: 0 0 0 1000px #f8fafc inset !important;
            -webkit-text-fill-color: #000000 !important;
        }}
        [data-testid="stAppViewContainer"] main input:focus::placeholder {{
            color: transparent !important;
            -webkit-text-fill-color: transparent !important;
        }}

        ::placeholder {{
            color: #64748b !important;
            -webkit-text-fill-color: #64748b !important;
            font-weight: 500 !important;
        }}

        /* Abas no Login com letras PRETAS */
        [data-testid="stTabs"] button[role="tab"] {{
            color: #000000 !important;
            font-weight: 800 !important;
            background: #e2e8f0 !important;
            border-radius: 10px !important;
            padding: 0.55rem 1.25rem !important;
            border: 1px solid #cbd5e1 !important;
        }}

        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
            background: #f5c400 !important;
            color: #000000 !important;
            border: 1px solid #eab308 !important;
            box-shadow: 0 4px 12px rgba(245, 196, 0, 0.35) !important;
        }}

        /* Botão com texto em PRETO */
        div[data-testid="stForm"] button[kind="primary"] {{
            background: linear-gradient(135deg, #f5c400 0%, #eab308 100%) !important;
            border: none !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 16px rgba(245, 196, 0, 0.35) !important;
        }}

        div[data-testid="stForm"] button[kind="primary"] p {{
            color: #000000 !important;
            font-weight: 800 !important;
            font-size: 1.05rem !important;
        }}

        /* Foto / Logo centralizada no menu de login */
        .st-key-card_login_box [data-testid="stImage"] {{
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            margin: 0 auto 0.8rem auto !important;
            text-align: center !important;
        }}

        .st-key-card_login_box [data-testid="stImage"] img {{
            border-radius: 50% !important;
            border: 3px solid #f5c400 !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35), 0 0 25px rgba(245, 196, 0, 0.4) !important;
            margin: 0 auto !important;
            display: block !important;
            object-fit: cover !important;
        }}
        """
    )

    st.write("")
    with st.container(border=True, key="card_login_box"):
        if CAMINHO_LOGO and os.path.isfile(CAMINHO_LOGO):
            st.image(CAMINHO_LOGO, width=170)
        elif LOGO_BASE64:
            st.image(BytesIO(base64.b64decode(LOGO_BASE64)), width=170)

        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 1.2rem; margin-top: 0.4rem;">
                <span style="display: inline-block; background: #f5c400; color: #000000; border-radius: 20px; padding: 5px 16px; font-size: 0.82rem; font-weight: 800; letter-spacing: 0.05em; margin-bottom: 0.6rem;">
                    ⚡ KW ALTA PERFORMANCE
                </span>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; color: #000000;">Acesse sua conta</h2>
                <p style="color: #1f2937; font-size: 0.95rem; margin: 0; font-weight: 600;">
                    Plataforma de Gestão e Treinamento Esportivo Personalizado
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        aba_entrar, aba_cadastro = st.tabs(["🔑 Entrar no Sistema", "📝 Criar Usuário"])
        usuarios = carregar_usuarios()

        with aba_entrar:
            with st.form("form_login"):
                usuario = st.text_input("Usuário", key="login_usuario", placeholder="Digite seu usuário").strip().lower()
                senha = st.text_input("Senha", type="password", key="login_senha", placeholder="Digite sua senha")
                entrar = st.form_submit_button("Entrar no Painel", type="primary", use_container_width=True)
            if entrar:
                usuario_alvo = "william" if usuario in {"wilian", "willian"} and usuario not in usuarios else usuario
                registro = usuarios.get(usuario_alvo)
                if registro and hmac.compare_digest(
                    gerar_hash_senha(senha, registro["salt"]), registro["hash"]
                ):
                    if eh_administrador(usuario_alvo) and registro.get("tipo") != "admin":
                        registro["tipo"] = "admin"
                        salvar_usuarios(usuarios)
                    st.session_state.usuario_autenticado = usuario_alvo
                    definir_sessao_url(gerar_token_sessao(usuario_alvo, registro))
                    st.rerun()
                st.error("Usuário ou senha incorretos.")

        with aba_cadastro:
            st.caption("A nova conta será de atleta/aluno. Somente Leo e William são administradores.")
            with st.form("form_cadastro"):
                novo_usuario = st.text_input("Nome de usuário", key="cadastro_usuario", placeholder="Ex: joaosilva").strip().lower()
                nova_senha = st.text_input("Senha (mínimo de 8 caracteres)", type="password", key="cadastro_senha", placeholder="Mínimo 8 caracteres")
                confirmar_senha = st.text_input("Confirme a senha", type="password", key="confirmar_senha", placeholder="Repita a senha")
                cadastrar = st.form_submit_button("Criar Minha Conta de Aluno", type="primary", use_container_width=True)
            if cadastrar:
                if len(novo_usuario) < 3 or len(novo_usuario) > 32:
                    st.error("O usuário deve ter entre 3 e 32 caracteres.")
                elif not all(caractere.isalnum() or caractere in "._-" for caractere in novo_usuario):
                    st.error("Use apenas letras, números, ponto, hífen ou sublinhado no usuário.")
                elif novo_usuario in usuarios or novo_usuario in ADMINS_AUTORIZADOS:
                    st.error("Esse usuário já existe ou está reservado.")
                elif len(nova_senha) < 8:
                    st.error("A senha deve ter pelo menos 8 caracteres.")
                elif nova_senha != confirmar_senha:
                    st.error("As senhas não coincidem.")
                else:
                    salt = secrets.token_hex(16)
                    novo_reg = {
                        "salt": salt,
                        "hash": gerar_hash_senha(nova_senha, salt),
                        "tipo": "usuario",  # SOMENTE LEO E WILLIAM SÃO ADMINS
                        "conta_admin": "leo",
                        "aluno": novo_usuario
                    }
                    usuarios[novo_usuario] = novo_reg
                    salvar_usuarios(usuarios)
                    st.session_state.usuario_autenticado = novo_usuario
                    definir_sessao_url(gerar_token_sessao(novo_usuario, novo_reg))
                    st.rerun()

# ==========================================
# CONTROLE DE SESSÃO E ACESSO
# ==========================================
usuarios = carregar_usuarios()

# Se não estiver no session_state, tenta restaurar sessão salva na URL (evita desconectar no reload F5)
if not st.session_state.get("usuario_autenticado"):
    token_sessao = obter_sessao_url()
    if token_sessao:
        usuario_recuperado = validar_token_sessao(token_sessao, usuarios)
        if usuario_recuperado:
            st.session_state.usuario_autenticado = usuario_recuperado
        else:
            limpar_sessao_url()

if not st.session_state.get("usuario_autenticado"):
    mostrar_tela_login()
    st.stop()

injetar_fundo_dashboard()
usuario_autenticado = st.session_state.usuario_autenticado
if usuario_autenticado in {"wilian", "willian"} and "william" in usuarios:
    usuario_autenticado = "william"
    st.session_state.usuario_autenticado = "william"
registro_usuario = usuarios.get(usuario_autenticado)
if not registro_usuario:
    limpar_sessao_url()
    st.session_state.pop("usuario_autenticado", None)
    st.stop()

# Garante que o token de sessão esteja gravado na URL do navegador para futuros recarregamentos
token_atual = obter_sessao_url()
if not token_atual or validar_token_sessao(token_atual, usuarios) != usuario_autenticado:
    definir_sessao_url(gerar_token_sessao(usuario_autenticado, registro_usuario))

# SOMENTE LEO E WILLIAM SÃO ADMINISTRADORES
eh_admin = eh_administrador(usuario_autenticado)
contas_admin = [adm for adm in ["leo", "william"] if adm in usuarios]
if not contas_admin:
    contas_admin = ["leo", "william"]
conta_admin = "leo" if "leo" in contas_admin else contas_admin[0]
if not eh_admin and not conta_admin:
    st.error("Nenhuma conta administradora está configurada.")
    st.stop()

if eh_admin:
    conta_ativa = st.session_state.get("admin_conta_ativa", usuario_autenticado)
    if conta_ativa not in contas_admin:
        conta_ativa = usuario_autenticado
    conta_dados = conta_ativa
    dados_conta = carregar_dados(conta_dados)
    aluno_atribuido = None
else:
    conta_admin_usuario = registro_usuario.get("conta_admin")
    aluno_atribuido = registro_usuario.get("aluno")
    conta_dados = conta_admin_usuario if conta_admin_usuario in contas_admin else None
    dados_conta = carregar_dados(conta_dados) if conta_dados else {}

    if not aluno_atribuido or aluno_atribuido not in dados_conta:
        contas_com_dados = {
            admin: dados_conta if admin == conta_dados else carregar_dados(admin)
            for admin in contas_admin
        }
        candidatos = [
            (admin, nome)
            for admin, alunos in contas_com_dados.items()
            for nome in alunos
            if aluno_atribuido and nome == aluno_atribuido
        ]
        if not candidatos:
            candidatos = [
                (admin, nome)
                for admin, alunos in contas_com_dados.items()
                for nome in alunos
                if nome.casefold() == usuario_autenticado.casefold()
            ]
            alunos_com_treino = [
                candidato for candidato in candidatos
                if contas_com_dados[candidato[0]][candidato[1]].get("treinos")
            ]
            if len(alunos_com_treino) == 1:
                candidatos = alunos_com_treino
            correspondencias_exatas = [
                candidato for candidato in candidatos
                if candidato[1] == usuario_autenticado
            ]
            if correspondencias_exatas:
                candidatos = correspondencias_exatas

        if len(candidatos) == 1:
            conta_dados, aluno_atribuido = candidatos[0]
            dados_conta = contas_com_dados[conta_dados]
            registro_usuario["conta_admin"] = conta_dados
            registro_usuario["aluno"] = aluno_atribuido
            salvar_usuarios(usuarios)
        else:
            if not conta_dados:
                conta_dados = conta_admin
                dados_conta = contas_com_dados[conta_dados]
            aluno_atribuido = None

chave_sessao_dados = (conta_dados, usuario_autenticado, aluno_atribuido)
if st.session_state.get("usuario_dados") != chave_sessao_dados:
    if eh_admin:
        st.session_state.db = dados_conta
    elif aluno_atribuido in dados_conta:
        st.session_state.db = {aluno_atribuido: dados_conta[aluno_atribuido]}
    else:
        st.session_state.db = {}
    st.session_state.usuario_dados = chave_sessao_dados

def atualizar_db():
    if not eh_admin:
        raise PermissionError("Somente o administrador pode alterar os treinos.")
    salvar_dados(st.session_state.db, conta_dados)

def salvar_video_em_catalogo_e_atletas(
    modalidade,
    nome_exercicio,
    referencia_video,
    salvar_catalogo=True,
    atualizar_todos_atletas=False,
    aluno_especifico=None,
    indice_treino_especifico=None,
):
    """Salva o vídeo no exercício do atleta e/ou no catálogo da modalidade e propaga se solicitado."""
    if not eh_admin:
        raise PermissionError("Somente os administradores podem alterar vídeos.")

    ref_limpa = str(referencia_video or "").strip()
    mod_limpa = str(modalidade or "").strip()
    ex_limpo = str(nome_exercicio or "").strip()

    if salvar_catalogo and mod_limpa and ex_limpo:
        catalogo = obter_catalogo_sessao()
        chave = f"{mod_limpa}::{ex_limpo}"
        if ref_limpa:
            catalogo[chave] = {
                "modalidade": mod_limpa,
                "exercicio": ex_limpo,
                "url_video": ref_limpa,
            }
        else:
            catalogo.pop(chave, None)
        salvar_catalogo_videos(catalogo)

    alterou_db = False
    if aluno_especifico and aluno_especifico in st.session_state.db:
        lista_t = st.session_state.db[aluno_especifico].get("treinos", [])
        if indice_treino_especifico is not None and 0 <= indice_treino_especifico < len(lista_t):
            lista_t[indice_treino_especifico]["url_video"] = ref_limpa
            alterou_db = True
        elif ex_limpo:
            for t in lista_t:
                if str(t.get("exercicio", "")).strip().casefold() == ex_limpo.casefold():
                    t["url_video"] = ref_limpa
                    alterou_db = True

    if atualizar_todos_atletas and ex_limpo:
        for dados_al in st.session_state.db.values():
            if not isinstance(dados_al, dict):
                continue
            for t in dados_al.get("treinos", []):
                if str(t.get("exercicio", "")).strip().casefold() == ex_limpo.casefold():
                    t["url_video"] = ref_limpa
                    alterou_db = True

    if alterou_db:
        atualizar_db()

def renderizar_central_videos_admin(aluno_contexto=None, sufixo="adm"):
    """Renderiza a aba exclusiva de administradores para gravar e adicionar vídeos para cada exercício."""
    if not eh_admin:
        st.error("Acesso restrito aos administradores.")
        return

    catalogo_videos = obter_catalogo_sessao()

    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(245, 196, 0, 0.14) 0%, rgba(15, 23, 42, 0.82) 100%), url('data:image/jpeg;base64,{LOGO_BASE64 or ""}') center center / contain no-repeat; background-color: #0b1120; border: 1px solid rgba(245, 196, 0, 0.38); border-radius: 20px; padding: 1.3rem 1.5rem; margin-bottom: 1.2rem;">
            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                <span style="font-size: 2.1rem;">🎬</span>
                <div>
                    <span class="kn-chip" style="font-size: 0.75rem; padding: 3px 10px; margin-bottom: 4px;">🔒 EXCLUSIVO ADMINISTRADORES (LEO & WILLIAM)</span>
                    <h3 style="margin: 4px 0 2px; color: #ffffff;">Central de Gravação e Vídeos dos Exercícios</h3>
                    <p style="margin: 0; color: #cbd5e1; font-size: 0.92rem;">
                        Grave vídeos na hora pela câmera, envie vídeos da galeria/aparelho ou adicione links do YouTube para cada exercício.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ==========================================
    # PAINEL 1: ESTÚDIO DE GRAVAÇÃO E ENVIO RÁPIDO
    # ==========================================
    with st.container(border=True):
        st.markdown("#### 🔴 Estúdio Rápido: Gravar ou Colocar Vídeo em um Exercício")
        st.caption("Escolha abaixo o exercício alvo e depois grave pela câmera, envie do celular/computador ou cole um link:")

        opcoes_escopo = []
        if aluno_contexto and aluno_contexto in st.session_state.db:
            opcoes_escopo.append(f"🏋️ Exercícios da Ficha de {aluno_contexto}")
        opcoes_escopo.append("📚 Exercícios por Modalidade (Catálogo Geral de Exercícios)")
        if not aluno_contexto and st.session_state.db:
            opcoes_escopo.append("👤 Escolher um Atleta Específico")

        escopo_sel = st.radio(
            "Onde deseja adicionar o vídeo?",
            opcoes_escopo,
            horizontal=True,
            key=f"rd_escopo_vid_{sufixo}_{aluno_contexto or 'geral'}",
        )

        atleta_alvo = aluno_contexto
        idx_treino_alvo = None
        modalidade_alvo = "Futebol"
        exercicio_alvo = ""

        if escopo_sel.startswith("🏋️") and atleta_alvo in st.session_state.db:
            dados_atl = st.session_state.db[atleta_alvo]
            modalidade_alvo = dados_atl.get("modalidade", "Futebol")
            treinos_atl = dados_atl.get("treinos", [])
            exercicios_mod = obter_exercicios_modalidade(modalidade_alvo, catalogo_videos)

            if treinos_atl:
                opcoes_t = [
                    f"{idx + 1}. {t.get('exercicio', 'Exercício')} ({t.get('series', 3)}x {t.get('reps', '10 a 12')}) — {'✅ Com vídeo' if (t.get('url_video') or obter_video_catalogo(modalidade_alvo, t.get('exercicio', ''), catalogo_videos)) else '⚠️ Sem vídeo'}"
                    for idx, t in enumerate(treinos_atl)
                ] + ["➕ Adicionar em outro exercício da modalidade"]
                escolha_t = st.selectbox(
                    f"Selecione o Exercício de {atleta_alvo}:",
                    range(len(opcoes_t)),
                    format_func=lambda i: opcoes_t[i],
                    key=f"sb_est_treino_atl_{sufixo}_{atleta_alvo}",
                )
                if escolha_t < len(treinos_atl):
                    idx_treino_alvo = escolha_t
                    exercicio_alvo = treinos_atl[escolha_t].get("exercicio", "")
                else:
                    c_ex_m, c_ex_novo = st.columns(2)
                    with c_ex_m:
                        ex_mod_sel = st.selectbox(
                            f"Exercício de {MODALIDADES_ICONES.get(modalidade_alvo, modalidade_alvo)}:",
                            exercicios_mod + ["+ Digitar novo exercício"],
                            key=f"sb_est_ex_extra_{sufixo}_{atleta_alvo}",
                        )
                    with c_ex_novo:
                        ex_novo_dig = st.text_input(
                            "Ou digite o nome do exercício:",
                            key=f"txt_est_ex_extra_{sufixo}_{atleta_alvo}",
                        )
                    exercicio_alvo = ex_novo_dig.strip() if ex_novo_dig.strip() else (
                        ex_mod_sel if ex_mod_sel != "+ Digitar novo exercício" else ""
                    )
            else:
                st.info(f"A ficha de **{atleta_alvo}** ainda não tem exercícios. Escolha abaixo o exercício para já adicioná-lo com vídeo:")
                c_ex_m, c_ex_novo = st.columns(2)
                with c_ex_m:
                    ex_mod_sel = st.selectbox(
                        f"Exercício de {MODALIDADES_ICONES.get(modalidade_alvo, modalidade_alvo)}:",
                        exercicios_mod + ["+ Digitar novo exercício"],
                        key=f"sb_est_vazio_ex_{sufixo}_{atleta_alvo}",
                    )
                with c_ex_novo:
                    ex_novo_dig = st.text_input(
                        "Ou digite o nome do exercício:",
                        key=f"txt_est_vazio_ex_{sufixo}_{atleta_alvo}",
                    )
                exercicio_alvo = ex_novo_dig.strip() if ex_novo_dig.strip() else (
                    ex_mod_sel if ex_mod_sel != "+ Digitar novo exercício" else ""
                )

        elif escopo_sel.startswith("👤"):
            nomes_atletas = list(st.session_state.db.keys())
            c_atl_sel, c_ex_atl_sel = st.columns(2)
            with c_atl_sel:
                atleta_alvo = st.selectbox(
                    "Selecione o Atleta:",
                    nomes_atletas,
                    key=f"sb_est_qualquer_atl_{sufixo}",
                )
            dados_atl = st.session_state.db.get(atleta_alvo, {})
            modalidade_alvo = dados_atl.get("modalidade", "Futebol")
            treinos_atl = dados_atl.get("treinos", [])
            with c_ex_atl_sel:
                if treinos_atl:
                    idx_treino_alvo = st.selectbox(
                        "Exercício da Ficha:",
                        range(len(treinos_atl)),
                        format_func=lambda i: f"{i + 1}. {treinos_atl[i].get('exercicio', 'Exercício')} ({'✅ Com vídeo' if treinos_atl[i].get('url_video') else '⚠️ Sem vídeo'})",
                        key=f"sb_est_qualquer_t_{sufixo}_{atleta_alvo}",
                    )
                    exercicio_alvo = treinos_atl[idx_treino_alvo].get("exercicio", "")
                else:
                    exercicios_mod = obter_exercicios_modalidade(modalidade_alvo, catalogo_videos)
                    exercicio_alvo = st.selectbox(
                        "Exercício da Modalidade (será adicionado ao atleta):",
                        exercicios_mod,
                        key=f"sb_est_qualquer_mod_ex_{sufixo}_{atleta_alvo}",
                    )
        else:
            atleta_alvo = None
            idx_treino_alvo = None
            mod_padrao = (
                st.session_state.db[aluno_contexto].get("modalidade", "Futebol")
                if aluno_contexto and aluno_contexto in st.session_state.db
                else "Futebol"
            )
            lista_mods = list(MODALIDADES_EXERCICIOS.keys())
            idx_mod = lista_mods.index(mod_padrao) if mod_padrao in lista_mods else 0

            c_mod_cat, c_ex_cat, c_novo_cat = st.columns([1.1, 1.3, 1.1])
            with c_mod_cat:
                modalidade_alvo = st.selectbox(
                    "Modalidade:",
                    lista_mods,
                    index=idx_mod,
                    format_func=lambda m: MODALIDADES_ICONES.get(m, m),
                    key=f"sb_est_cat_mod_{sufixo}",
                )
            exercicios_mod = obter_exercicios_modalidade(modalidade_alvo, catalogo_videos)
            with c_ex_cat:
                ex_cat_sel = st.selectbox(
                    "Exercício:",
                    exercicios_mod + ["+ Cadastrar novo exercício"],
                    format_func=lambda e: (
                        e if e == "+ Cadastrar novo exercício"
                        else f"{e} {'(✅ Com vídeo)' if obter_video_catalogo(modalidade_alvo, e, catalogo_videos) else '(⚠️ Sem vídeo)'}"
                    ),
                    key=f"sb_est_cat_ex_{sufixo}_{modalidade_alvo}",
                )
            with c_novo_cat:
                ex_cat_novo = st.text_input(
                    "Ou Novo Exercício:",
                    placeholder="Digite se for novo...",
                    key=f"txt_est_cat_novo_{sufixo}_{modalidade_alvo}",
                )
            exercicio_alvo = ex_cat_novo.strip() if ex_cat_novo.strip() else (
                ex_cat_sel if ex_cat_sel != "+ Cadastrar novo exercício" else ""
            )

        chave_estudio = f"est_{sufixo}_{re.sub(r'[^a-z0-9]+', '_', (modalidade_alvo + '_' + exercicio_alvo).lower())[:28]}"

        aba_gravar_enviar, aba_link_url = st.tabs([
            "📷 1. Gravar Vídeo na Hora ou Enviar Arquivo (Câmera / Celular / PC)",
            "🔗 2. Colar Link de Vídeo (YouTube / Shorts / Internet)",
        ])

        with aba_gravar_enviar:
            col_cam_live, col_upload_file = st.columns([1.15, 1], gap="large")
            with col_cam_live:
                st.markdown("**🎥 Opção A — Gravar Ao Vivo pela Câmera do Navegador:**")
                renderizar_gravador_camera_html(chave_estudio, exercicio_alvo or "exercicio")

            with col_upload_file:
                st.markdown("**📁 Opção B — Gravar pela Câmera do Celular ou Escolher Vídeo da Galeria/PC:**")
                st.info(
                    "💡 **No celular:** toque em **Browse files** abaixo e escolha **Câmera / Filmadora** para gravar na hora, ou escolha um vídeo pronto da sua **Galeria**.\n\n"
                    "💡 **No computador:** grave ao lado e clique em **'4. Anexar Vídeo Gravado'** ou selecione um arquivo de vídeo do PC."
                )
                with st.container(key=f"box_up_vid_{chave_estudio}"):
                    arquivo_vid_est = st.file_uploader(
                        f"Selecionar ou Gravar Vídeo para '{exercicio_alvo or 'Exercício'}'",
                        type=["mp4", "mov", "webm", "avi", "mkv", "m4v", "3gp"],
                        key=f"file_up_vid_{chave_estudio}",
                    )

                salvar_padrao_cat = st.checkbox(
                    f"📌 Salvar como vídeo padrão de '{exercicio_alvo or 'exercício'}' em {MODALIDADES_ICONES.get(modalidade_alvo, modalidade_alvo)}",
                    value=True,
                    key=f"chk_cat_up_{chave_estudio}",
                )
                propagar_todos_up = st.checkbox(
                    "🔄 Aplicar também em todos os atletas que possuem este exercício",
                    value=True,
                    key=f"chk_prop_up_{chave_estudio}",
                )

                if arquivo_vid_est is not None:
                    st.success(f"🎬 Vídeo pronto para salvar: **{arquivo_vid_est.name}** ({arquivo_vid_est.size / 1024:.0f} KB)")
                    try:
                        st.video(arquivo_vid_est)
                    except Exception:
                        pass

                if st.button(
                    f"💾 Salvar Vídeo Gravado/Enviado em '{exercicio_alvo or 'Exercício'}'",
                    type="primary",
                    use_container_width=True,
                    key=f"btn_salvar_arq_est_{chave_estudio}",
                ):
                    if not exercicio_alvo:
                        st.error("Selecione ou digite o nome do exercício primeiro.")
                    elif arquivo_vid_est is None:
                        st.error("Grave um vídeo na câmera ao lado (e clique em '4. Anexar Vídeo Gravado') ou selecione um arquivo de vídeo na caixa acima.")
                    else:
                        try:
                            ref_salva = salvar_arquivo_video_upload(arquivo_vid_est, f"{modalidade_alvo}_{exercicio_alvo}")
                            # Se o atleta foi selecionado mas ainda não tinha o exercício na ficha, adiciona
                            if atleta_alvo and atleta_alvo in st.session_state.db and idx_treino_alvo is None:
                                st.session_state.db[atleta_alvo].setdefault("treinos", []).append({
                                    "exercicio": exercicio_alvo,
                                    "series": 3,
                                    "reps": "10 a 12",
                                    "url_video": ref_salva,
                                    "observacoes": "",
                                })
                                idx_treino_alvo = len(st.session_state.db[atleta_alvo]["treinos"]) - 1

                            salvar_video_em_catalogo_e_atletas(
                                modalidade=modalidade_alvo,
                                nome_exercicio=exercicio_alvo,
                                referencia_video=ref_salva,
                                salvar_catalogo=salvar_padrao_cat,
                                atualizar_todos_atletas=propagar_todos_up,
                                aluno_especifico=atleta_alvo,
                                indice_treino_especifico=idx_treino_alvo,
                            )
                            notificar_sucesso(f"Vídeo salvo para '{exercicio_alvo}'!", "🎥")
                            st.success(f"✅ Vídeo de **{exercicio_alvo}** salvo com sucesso!")
                            st.rerun()
                        except Exception as erro_v:
                            st.error(f"Erro ao salvar vídeo: {erro_v}")

        with aba_link_url:
            video_atual_est = ""
            if atleta_alvo and idx_treino_alvo is not None:
                treinos_tmp = st.session_state.db.get(atleta_alvo, {}).get("treinos", [])
                if 0 <= idx_treino_alvo < len(treinos_tmp):
                    video_atual_est = treinos_tmp[idx_treino_alvo].get("url_video", "")
            if not video_atual_est and exercicio_alvo:
                video_atual_est = obter_video_catalogo(modalidade_alvo, exercicio_alvo, catalogo_videos)

            val_link_inicial = "" if str(video_atual_est).startswith("arquivo_local:") else str(video_atual_est or "")
            link_digitado = st.text_input(
                f"URL do Vídeo para '{exercicio_alvo or 'Exercício'}' (YouTube, Shorts, Vimeo ou Link Direto .mp4):",
                value=val_link_inicial,
                placeholder="https://www.youtube.com/watch?v=...",
                key=f"txt_link_est_{chave_estudio}",
            )
            c_chk1, c_chk2 = st.columns(2)
            with c_chk1:
                salvar_padrao_link = st.checkbox(
                    f"📌 Salvar como vídeo padrão de '{exercicio_alvo or 'exercício'}'",
                    value=True,
                    key=f"chk_cat_lnk_{chave_estudio}",
                )
            with c_chk2:
                propagar_todos_link = st.checkbox(
                    "🔄 Aplicar em todos os atletas com este exercício",
                    value=True,
                    key=f"chk_prop_lnk_{chave_estudio}",
                )

            if st.button(
                f"💾 Salvar Link de Vídeo em '{exercicio_alvo or 'Exercício'}'",
                type="primary",
                use_container_width=True,
                key=f"btn_salvar_link_est_{chave_estudio}",
            ):
                if not exercicio_alvo:
                    st.error("Selecione ou digite o nome do exercício.")
                elif not link_digitado.strip():
                    st.error("Cole um link válido de vídeo.")
                else:
                    ref_link = normalizar_url_video(link_digitado.strip())
                    if atleta_alvo and atleta_alvo in st.session_state.db and idx_treino_alvo is None:
                        st.session_state.db[atleta_alvo].setdefault("treinos", []).append({
                            "exercicio": exercicio_alvo,
                            "series": 3,
                            "reps": "10 a 12",
                            "url_video": ref_link,
                            "observacoes": "",
                        })
                        idx_treino_alvo = len(st.session_state.db[atleta_alvo]["treinos"]) - 1

                    salvar_video_em_catalogo_e_atletas(
                        modalidade=modalidade_alvo,
                        nome_exercicio=exercicio_alvo,
                        referencia_video=ref_link,
                        salvar_catalogo=salvar_padrao_link,
                        atualizar_todos_atletas=propagar_todos_link,
                        aluno_especifico=atleta_alvo,
                        indice_treino_especifico=idx_treino_alvo,
                    )
                    notificar_sucesso(f"Link de vídeo salvo para '{exercicio_alvo}'!", "🔗")
                    st.success(f"✅ Link de vídeo salvo em **{exercicio_alvo}**!")
                    st.rerun()

    st.write("")

    # ==========================================
    # PAINEL 2: VÍDEOS DE CADA EXERCÍCIO DO ATLETA ATUAL
    # ==========================================
    if aluno_contexto and aluno_contexto in st.session_state.db:
        dados_al_ctx = st.session_state.db[aluno_contexto]
        mod_ctx = dados_al_ctx.get("modalidade", "Futebol")
        treinos_ctx = dados_al_ctx.get("treinos", [])

        st.markdown(f"#### 🏋️ Vídeos de Cada Exercício de {aluno_contexto} ({MODALIDADES_ICONES.get(mod_ctx, mod_ctx)})")
        if not treinos_ctx:
            st.info(f"Nenhum exercício cadastrado ainda para {aluno_contexto}. Use o painel acima ou a aba 'Plano de Treino' para adicionar.")
        else:
            for idx_ex, item_t in enumerate(treinos_ctx):
                nome_ex_item = item_t.get("exercicio", "Exercício")
                vid_proprio = item_t.get("url_video", "").strip()
                vid_catalogo = obter_video_catalogo(mod_ctx, nome_ex_item, catalogo_videos)
                vid_efetivo = vid_proprio or vid_catalogo
                status_badge = "✅ Com Vídeo" if vid_efetivo else "⚠️ Sem Vídeo"

                with st.expander(f"🎬 {idx_ex + 1}. {nome_ex_item} ({item_t.get('series', 3)}x {item_t.get('reps', '10 a 12')})  •  {status_badge}", expanded=not bool(vid_efetivo)):
                    c_form_ex, c_prev_ex = st.columns([1.15, 1], gap="large")
                    slug_al = re.sub(r"[^a-z0-9]+", "_", str(aluno_contexto).lower()).strip("_")
                    chave_card = f"card_atl_{sufixo}_{slug_al}_{idx_ex}"

                    with c_form_ex:
                        with st.container(key=f"box_up_vid_{chave_card}"):
                            up_card = st.file_uploader(
                                f"📁 Enviar ou Gravar Vídeo pelo Celular/PC para '{nome_ex_item}'",
                                type=["mp4", "mov", "webm", "avi", "mkv", "m4v", "3gp"],
                                key=f"up_file_{chave_card}",
                            )
                        url_card = st.text_input(
                            "🔗 Ou Link do Vídeo (YouTube / Shorts / MP4)",
                            value="" if vid_efetivo.startswith("arquivo_local:") else vid_efetivo,
                            placeholder="https://www.youtube.com/watch?v=...",
                            key=f"txt_url_{chave_card}",
                        )
                        abrir_cam_card = st.checkbox(
                            "📷 Abrir gravador de câmera ao vivo neste exercício",
                            key=f"chk_cam_{chave_card}",
                        )
                        if abrir_cam_card:
                            renderizar_gravador_camera_html(chave_card, nome_ex_item)

                        b_col1, b_col2 = st.columns([2, 1])
                        with b_col1:
                            if st.button("💾 Salvar Vídeo neste Exercício", type="primary", use_container_width=True, key=f"btn_save_{chave_card}"):
                                try:
                                    if up_card is not None:
                                        nova_ref = salvar_arquivo_video_upload(up_card, f"{mod_ctx}_{nome_ex_item}")
                                    elif url_card.strip():
                                        nova_ref = normalizar_url_video(url_card.strip())
                                    else:
                                        nova_ref = ""

                                    if not nova_ref:
                                        st.warning("Envie/grave um arquivo de vídeo ou informe um link antes de salvar.")
                                    else:
                                        salvar_video_em_catalogo_e_atletas(
                                            modalidade=mod_ctx,
                                            nome_exercicio=nome_ex_item,
                                            referencia_video=nova_ref,
                                            salvar_catalogo=True,
                                            atualizar_todos_atletas=False,
                                            aluno_especifico=aluno_contexto,
                                            indice_treino_especifico=idx_ex,
                                        )
                                        notificar_sucesso(f"Vídeo salvo em '{nome_ex_item}'!", "🎥")
                                        st.rerun()
                                except Exception as e_card:
                                    st.error(f"Erro ao salvar vídeo: {e_card}")
                        with b_col2:
                            if vid_efetivo:
                                if st.button("🗑️ Remover Vídeo", use_container_width=True, key=f"btn_del_vid_{chave_card}"):
                                    item_t["url_video"] = ""
                                    atualizar_db()
                                    notificar_sucesso(f"Vídeo removido de '{nome_ex_item}'.", "🗑️")
                                    st.rerun()

                    with c_prev_ex:
                        if vid_efetivo:
                            origem_txt = "📁 Vídeo Gravado/Enviado no Sistema" if vid_efetivo.startswith("arquivo_local:") else "🔗 Link de Vídeo"
                            st.caption(f" Status: **{origem_txt}**")
                            exibir_player_video(vid_efetivo)
                        else:
                            st.markdown(
                                """
                                <div class="kn-empty-video">
                                    <span style="font-size: 2rem;">🎬</span>
                                    <span style="color: #64748b; font-size: 0.88rem;">Nenhum vídeo adicionado para este exercício</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

        st.divider()

    # ==========================================
    # PAINEL 3: CATÁLOGO DE VÍDEOS DE TODOS OS EXERCÍCIOS POR MODALIDADE
    # ==========================================
    st.markdown("#### 📚 Vídeos Padrão de Cada Exercício por Modalidade")
    st.caption("Adicione ou grave o vídeo de cada exercício da modalidade. Sempre que você adicionar esse exercício para qualquer atleta, o vídeo já entrará automaticamente!")

    lista_modalidades = list(MODALIDADES_EXERCICIOS.keys())
    mod_inicial = (
        st.session_state.db[aluno_contexto].get("modalidade", "Futebol")
        if aluno_contexto and aluno_contexto in st.session_state.db
        else "Futebol"
    )
    idx_m_cat = lista_modalidades.index(mod_inicial) if mod_inicial in lista_modalidades else 0

    mod_catalogo_sel = st.selectbox(
        "Selecione a Modalidade para gerenciar os vídeos de cada exercício:",
        lista_modalidades,
        index=idx_m_cat,
        format_func=lambda m: MODALIDADES_ICONES.get(m, m),
        key=f"sb_gerenciar_cat_mod_{sufixo}",
    )

    exercicios_da_modalidade = obter_exercicios_modalidade(mod_catalogo_sel, catalogo_videos)
    com_video_count = sum(bool(obter_video_catalogo(mod_catalogo_sel, ex, catalogo_videos)) for ex in exercicios_da_modalidade)
    st.caption(f"Modalidade **{MODALIDADES_ICONES.get(mod_catalogo_sel, mod_catalogo_sel)}**: **{com_video_count} de {len(exercicios_da_modalidade)}** exercícios possuem vídeo cadastrado.")

    for idx_m_ex, nome_ex_mod in enumerate(exercicios_da_modalidade):
        vid_cat_atual = obter_video_catalogo(mod_catalogo_sel, nome_ex_mod, catalogo_videos)
        icone_status = "✅ Com Vídeo" if vid_cat_atual else "⚠️ Sem Vídeo"
        chave_item_cat = f"cat_{sufixo}_{re.sub(r'[^a-z0-9]+', '_', (mod_catalogo_sel + '_' + nome_ex_mod).lower())}_{idx_m_ex}"

        with st.expander(f"{MODALIDADES_ICONES.get(mod_catalogo_sel, mod_catalogo_sel)}  •  {nome_ex_mod}  —  {icone_status}", expanded=False):
            col_cat_ed, col_cat_vid = st.columns([1.15, 1], gap="large")
            with col_cat_ed:
                with st.container(key=f"box_up_vid_{chave_item_cat}"):
                    up_cat_item = st.file_uploader(
                        f"📁 Enviar / Gravar Vídeo para '{nome_ex_mod}'",
                        type=["mp4", "mov", "webm", "avi", "mkv", "m4v", "3gp"],
                        key=f"up_cat_{chave_item_cat}",
                    )
                url_cat_item = st.text_input(
                    f"🔗 Ou Link do Vídeo (YouTube / MP4) para '{nome_ex_mod}'",
                    value="" if vid_cat_atual.startswith("arquivo_local:") else vid_cat_atual,
                    placeholder="https://www.youtube.com/watch?v=...",
                    key=f"url_cat_{chave_item_cat}",
                )
                cam_cat_open = st.checkbox(
                    "📷 Gravar vídeo agora pela câmera",
                    key=f"cam_cat_{chave_item_cat}",
                )
                if cam_cat_open:
                    renderizar_gravador_camera_html(chave_item_cat, nome_ex_mod)

                bc1, bc2 = st.columns([2, 1])
                with bc1:
                    if st.button(
                        f"💾 Salvar Vídeo em '{nome_ex_mod}'",
                        type="primary",
                        use_container_width=True,
                        key=f"btn_save_cat_{chave_item_cat}",
                    ):
                        try:
                            if up_cat_item is not None:
                                ref_cat_nova = salvar_arquivo_video_upload(up_cat_item, f"{mod_catalogo_sel}_{nome_ex_mod}")
                            elif url_cat_item.strip():
                                ref_cat_nova = normalizar_url_video(url_cat_item.strip())
                            else:
                                ref_cat_nova = ""

                            if not ref_cat_nova:
                                st.warning("Selecione/grave um vídeo ou cole um link antes de salvar.")
                            else:
                                salvar_video_em_catalogo_e_atletas(
                                    modalidade=mod_catalogo_sel,
                                    nome_exercicio=nome_ex_mod,
                                    referencia_video=ref_cat_nova,
                                    salvar_catalogo=True,
                                    atualizar_todos_atletas=True,
                                )
                                notificar_sucesso(f"Vídeo de '{nome_ex_mod}' salvo e aplicado!", "🎥")
                                st.rerun()
                        except Exception as err_c:
                            st.error(f"Erro ao salvar: {err_c}")
                with bc2:
                    if vid_cat_atual:
                        if st.button("🗑️ Remover", use_container_width=True, key=f"btn_rem_cat_{chave_item_cat}"):
                            salvar_video_em_catalogo_e_atletas(
                                modalidade=mod_catalogo_sel,
                                nome_exercicio=nome_ex_mod,
                                referencia_video="",
                                salvar_catalogo=True,
                                atualizar_todos_atletas=False,
                            )
                            notificar_sucesso(f"Vídeo padrão removido de '{nome_ex_mod}'.", "🗑️")
                            st.rerun()

            with col_cat_vid:
                if vid_cat_atual:
                    exibir_player_video(vid_cat_atual)
                else:
                    st.markdown(
                        """
                        <div class="kn-empty-video">
                            <span style="font-size: 2rem;">🎬</span>
                            <span style="color: #64748b; font-size: 0.88rem;">Sem vídeo cadastrado para este exercício</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

if st.session_state.get("aviso_exclusao"):
    st.error(st.session_state.pop("aviso_exclusao"))

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    if CAMINHO_LOGO and os.path.exists(CAMINHO_LOGO):
        st.image(CAMINHO_LOGO, width=220)
    elif LOGO_BASE64:
        st.image(BytesIO(base64.b64decode(LOGO_BASE64)), width=220)
    else:
        st.markdown("### ⚡ KW ALTA PERFORMANCE")

    st.markdown(
        f"""
        <div class="kn-sidebar-user">
            <span style="font-size: 1.5rem;">{'👑' if eh_admin else '⚡'}</span>
            <div style="flex: 1; overflow: hidden;">
                <div style="font-weight: 700; color: #ffffff; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
                    {usuario_autenticado}
                </div>
                <div style="font-size: 0.75rem; color: {'#f5c400' if eh_admin else '#38bdf8'}; font-weight: 700; text-transform: uppercase;">
                    {'Administrador' if eh_admin else 'Atleta'}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sair = st.button("↩  Sair da conta", key="btn_logout", use_container_width=True)
    if sair:
        limpar_sessao_url()
        st.session_state.pop("usuario_autenticado", None)
        st.session_state.pop("db", None)
        st.session_state.pop("usuario_dados", None)
        st.rerun()

    st.divider()

    alunos_existentes = list(st.session_state.db.keys())
    aluno_atual = None

    if eh_admin:
        with st.expander("🖼️ Foto do Programa (Login e Fundo)"):
            st.caption("Altere a foto que aparece na tela inteira de login e no fundo do sistema:")
            nova_foto_sistema = st.file_uploader(
                "Selecionar imagem:",
                type=["jpg", "jpeg", "png", "webp"],
                key="upload_foto_sistema_bg",
                help="Envie qualquer imagem do seu computador ou celular para usar como tela cheia de login."
            )
            if nova_foto_sistema is not None:
                if st.button("💾 Salvar como Foto do Programa", type="primary", use_container_width=True, key="btn_salvar_foto_sistema"):
                    try:
                        caminho_salvar = os.path.join(DIRETORIO_APP, "foto_login.jpg")
                        img = Image.open(nova_foto_sistema).convert("RGB")
                        img.save(caminho_salvar, format="JPEG", quality=90, optimize=True)
                        st.cache_data.clear()
                        notificar_sucesso("Foto do programa atualizada!", "🖼️")
                        st.success("Nova foto salva com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar imagem: {e}")

            caminho_custom = os.path.join(DIRETORIO_APP, "foto_login.jpg")
            if os.path.isfile(caminho_custom):
                if st.button("🔄 Restaurar foto original", key="btn_restaurar_bg_app", use_container_width=True):
                    try:
                        os.remove(caminho_custom)
                        st.cache_data.clear()
                        notificar_sucesso("Foto original restaurada!", "🔄")
                        st.rerun()
                    except Exception:
                        pass

        with st.expander("🔐 Gerenciar Contas de Usuários (Apenas Admins)", expanded=False):
            st.caption("Controle de acessos do sistema. **Somente Leo e William são administradores.**")
            
            usuarios_ger = carregar_usuarios()
            itens_usuarios = sorted(
                usuarios_ger.items(),
                key=lambda item: (0 if eh_administrador(item[0]) else 1, item[0]),
            )
            for u_nome, u_info in itens_usuarios:
                eh_adm_u = eh_administrador(u_nome)
                col_u_info, col_u_acao = st.columns([2.3, 1.2], vertical_alignment="center")
                with col_u_info:
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                            <span>{'👑' if eh_adm_u else '🏃'}</span>
                            <strong style="color: #ffffff;">{u_nome}</strong>
                            <span class="{'kn-chip' if eh_adm_u else 'kn-chip-cyan'}" style="font-size: 0.72rem; padding: 2px 8px;">
                                {'Administrador' if eh_adm_u else 'Atleta'}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if not eh_adm_u:
                        aluno_vinc = u_info.get("aluno", "Mesmo nome")
                        st.caption(f"Ficha vinculada: **{aluno_vinc}**")
                
                with col_u_acao:
                    if not eh_adm_u:
                        if st.button("🗑️ Remover", key=f"btn_rem_user_sb_{u_nome}", use_container_width=True, help=f"Remover conta de {u_nome}"):
                            usuarios_ger.pop(u_nome, None)
                            remover_usuario(u_nome)
                            notificar_sucesso(f"Usuário {u_nome} removido!", "🗑️")
                            st.rerun()

            st.write("")
            st.markdown("##### 🔑 Redefinir Senha de Conta")
            with st.form("form_sb_redefinir_senha"):
                opcoes_usr_senha = [u for u, _ in itens_usuarios]
                usr_alvo_senha = st.selectbox("Conta", opcoes_usr_senha, key="sb_adm_redef_u")
                nova_senha_redef = st.text_input("Nova Senha", type="password", key="txt_adm_redef_s", placeholder="Mínimo 8 caracteres")
                if st.form_submit_button("Salvar Nova Senha na Nuvem", use_container_width=True):
                    if len(nova_senha_redef) < 8:
                        st.error("A nova senha deve ter pelo menos 8 caracteres.")
                    else:
                        novo_salt = secrets.token_hex(16)
                        usuarios_ger[usr_alvo_senha]["salt"] = novo_salt
                        usuarios_ger[usr_alvo_senha]["hash"] = gerar_hash_senha(nova_senha_redef, novo_salt)
                        usuarios_ger[usr_alvo_senha]["tipo"] = "admin" if eh_administrador(usr_alvo_senha) else "usuario"
                        salvar_usuarios(usuarios_ger)
                        notificar_sucesso(f"Senha de {usr_alvo_senha} atualizada na nuvem!", "🔑")
                        st.success(f"Senha de {usr_alvo_senha} atualizada!")
                        st.rerun()

            st.write("")
            st.markdown("##### ➕ Criar Nova Conta de Aluno")
            with st.form("form_sb_criar_usuario_aluno"):
                novo_u_aluno = st.text_input("Usuário do Aluno", placeholder="Ex.: novatleta", key="txt_adm_cad_u").strip().lower()
                nova_s_aluno = st.text_input("Senha", type="password", key="txt_adm_cad_s", placeholder="Mínimo 8 caracteres")
                vinc_opcoes = ["(Usar o mesmo nome)"] + alunos_existentes
                vinc_escolhido = st.selectbox("Vincular à Ficha do Atleta:", vinc_opcoes, key="sb_adm_vinc_atl")

                if st.form_submit_button("Cadastrar Conta de Aluno", type="primary", use_container_width=True):
                    if len(novo_u_aluno) < 3:
                        st.error("Usuário deve ter pelo menos 3 caracteres.")
                    elif novo_u_aluno in usuarios_ger or novo_u_aluno in ADMINS_AUTORIZADOS:
                        st.error("Este usuário já existe ou está reservado!")
                    elif len(nova_s_aluno) < 8:
                        st.error("A senha deve ter pelo menos 8 caracteres.")
                    else:
                        salt_novo = secrets.token_hex(16)
                        aluno_final = novo_u_aluno if vinc_escolhido == vinc_opcoes[0] else vinc_escolhido
                        usuarios_ger[novo_u_aluno] = {
                            "salt": salt_novo,
                            "hash": gerar_hash_senha(nova_s_aluno, salt_novo),
                            "tipo": "usuario",
                            "conta_admin": usuario_autenticado,
                            "aluno": aluno_final
                        }
                        salvar_usuarios(usuarios_ger)
                        notificar_sucesso(f"Conta de {novo_u_aluno} criada!", "✅")
                        st.success(f"Aluno {novo_u_aluno} cadastrado com sucesso!")
                        st.rerun()

        st.markdown("#### 👥 Gerenciar Atletas")
        
        # Sincroniza atleta selecionado com session_state
        if "sb_aluno_ver" not in st.session_state:
            st.session_state["sb_aluno_ver"] = 0

        aluno_salvo = st.session_state.get("aluno_selecionado")
        opcoes_aluno = ["-- Visão Geral (Todos) --"] + alunos_existentes
        idx_aluno = 0
        if aluno_salvo in alunos_existentes:
            idx_aluno = opcoes_aluno.index(aluno_salvo)
        
        opcao_aluno = st.selectbox(
            "Atleta Selecionado",
            opcoes_aluno,
            index=idx_aluno,
            key=f"sb_selecionar_aluno_{st.session_state['sb_aluno_ver']}"
        )

        if opcao_aluno != opcoes_aluno[idx_aluno]:
            if opcao_aluno == opcoes_aluno[0]:
                st.session_state["aluno_selecionado"] = None
            else:
                st.session_state["aluno_selecionado"] = opcao_aluno
            st.session_state["sb_aluno_ver"] = st.session_state.get("sb_aluno_ver", 0) + 1
            st.rerun()

        aluno_atual = st.session_state.get("aluno_selecionado")

        # Abas de Gerenciamento de Atletas: Cadastrar e Remover
        tab_cad_atl, tab_rem_atl = st.tabs(["➕ Cadastrar", "🗑️ Remover"])

        with tab_cad_atl:
            novo_nome = st.text_input("Nome do Atleta", placeholder="Ex.: Lucas Lima", key="txt_novo_aluno_nome")
            nova_modalidade = st.selectbox(
                "Modalidade",
                list(MODALIDADES_EXERCICIOS.keys()),
                format_func=lambda m: MODALIDADES_ICONES.get(m, m),
                key="sb_nova_modalidade_aluno"
            )

            if st.button("Cadastrar Atleta", type="primary", use_container_width=True, key="btn_cadastrar_aluno_sb"):
                nome_formatado = novo_nome.strip()
                if nome_formatado and nome_formatado not in st.session_state.db:
                    st.session_state.db[nome_formatado] = {
                        "modalidade": nova_modalidade,
                        "treinos": []
                    }
                    atualizar_db()
                    st.session_state["aluno_selecionado"] = nome_formatado
                    st.session_state["sb_aluno_ver"] = st.session_state.get("sb_aluno_ver", 0) + 1
                    notificar_sucesso(f"Atleta {nome_formatado} cadastrado!", "✅")
                    st.success(f"Atleta {nome_formatado} cadastrado com sucesso!")
                    st.rerun()
                elif nome_formatado in st.session_state.db:
                    st.error("Atleta já cadastrado!")
                else:
                    st.error("Informe o nome do atleta.")

        with tab_rem_atl:
            if not alunos_existentes:
                st.caption("Nenhum atleta para remover.")
            else:
                idx_rem = alunos_existentes.index(aluno_atual) if aluno_atual in alunos_existentes else 0
                atleta_para_remover = st.selectbox(
                    "Atleta a excluir",
                    alunos_existentes,
                    index=idx_rem,
                    key="sb_remover_atleta_sb"
                )
                st.caption(f"⚠️ Atenção: todos os treinos de **{atleta_para_remover}** serão excluídos.")
                
                if st.button("🗑️ Excluir Atleta", type="secondary", use_container_width=True, key="btn_del_atleta_sb"):
                    st.session_state[f"confirm_del_atleta_{atleta_para_remover}"] = True

                if st.session_state.get(f"confirm_del_atleta_{atleta_para_remover}"):
                    st.warning(f"Excluir **{atleta_para_remover}** e todos os seus treinos?")
                    c_sim, c_nao = st.columns(2)
                    with c_sim:
                        if st.button("Sim, excluir", key=f"btn_conf_del_atl_sim_{atleta_para_remover}", type="primary", use_container_width=True):
                            st.session_state.db.pop(atleta_para_remover, None)
                            atualizar_db()
                            # Limpa vínculos em usuarios.json se houver
                            usuarios_mod = carregar_usuarios()
                            alterou_user = False
                            for u_reg in usuarios_mod.values():
                                if u_reg.get("aluno") == atleta_para_remover:
                                    u_reg.pop("aluno", None)
                                    alterou_user = True
                            if alterou_user:
                                salvar_usuarios(usuarios_mod)

                            st.session_state["aluno_selecionado"] = None
                            st.session_state["sb_aluno_ver"] = st.session_state.get("sb_aluno_ver", 0) + 1
                            st.session_state.pop(f"confirm_del_atleta_{atleta_para_remover}", None)
                            notificar_sucesso(f"Atleta {atleta_para_remover} removido!", "🗑️")
                            st.rerun()
                    with c_nao:
                        if st.button("Cancelar", key=f"btn_conf_del_atl_nao_{atleta_para_remover}", use_container_width=True):
                            st.session_state.pop(f"confirm_del_atleta_{atleta_para_remover}", None)
                            st.rerun()

        st.divider()
        st.markdown("#### ➕ Adicionar Exercício")
        if aluno_atual and aluno_atual in st.session_state.db:
            modalidade_aluno = st.session_state.db[aluno_atual].get("modalidade", "Futebol")
            st.caption(f"Atleta: **{aluno_atual}** • {MODALIDADES_ICONES.get(modalidade_aluno, modalidade_aluno)}")

            if st.button("💾 Salvar Treino", key="btn_salvar_sidebar", type="primary", use_container_width=True):
                atualizar_db()
                notificar_sucesso(f"Treino de {aluno_atual} salvo com sucesso!", "💾")
                st.success(f"Treino de {aluno_atual} salvo!")

            lista_exercicios = obter_exercicios_modalidade(modalidade_aluno)
            opcao_personalizada = "+ Outro exercício"
            
            with st.form(f"form_add_ex_sidebar_{aluno_atual}"):
                exercicio_selecionado = st.selectbox(
                    "Exercício Sugerido",
                    lista_exercicios + [opcao_personalizada],
                    key=f"sb_ex_side_{aluno_atual}"
                )
                exercicio_customizado = st.text_input(
                    "Nome Personalizado (opcional)",
                    placeholder="Digite se for outro exercício...",
                    key=f"txt_custom_side_{aluno_atual}"
                )

                col_sets, col_reps = st.columns(2)
                series = col_sets.number_input("Séries", min_value=1, max_value=30, value=3, step=1, key=f"side_num_series_{aluno_atual}")
                reps = col_reps.text_input("Reps/Tempo", value="10 a 12", key=f"side_txt_reps_{aluno_atual}")

                url_video = st.text_input("URL do Vídeo (YouTube)", placeholder="https://youtube.com/...", key=f"side_txt_video_{aluno_atual}")
                arq_video_side = st.file_uploader(
                    "Ou Enviar/Gravar Vídeo (MP4, MOV, WEBM)",
                    type=["mp4", "mov", "webm", "avi", "mkv", "m4v", "3gp"],
                    key=f"side_file_video_{aluno_atual}",
                )
                observacoes = st.text_area("Orientações / Observações", placeholder="Ex: Manter tronco firme, foco na explosão...", key=f"side_txt_obs_{aluno_atual}")

                btn_add_side = st.form_submit_button("Adicionar ao Treino", type="primary", use_container_width=True)
                if btn_add_side:
                    nome_final = exercicio_customizado.strip() if exercicio_customizado.strip() else (
                        exercicio_selecionado if exercicio_selecionado != opcao_personalizada else ""
                    )
                    if not nome_final:
                        st.error("Digite ou selecione o nome do exercício.")
                    else:
                        video_final_side = url_video.strip()
                        if arq_video_side is not None:
                            try:
                                video_final_side = salvar_arquivo_video_upload(arq_video_side, f"{modalidade_aluno}_{nome_final}")
                                salvar_video_em_catalogo_e_atletas(modalidade_aluno, nome_final, video_final_side, salvar_catalogo=True)
                            except Exception as e_vid_s:
                                st.error(f"Erro ao salvar vídeo: {e_vid_s}")
                        elif not video_final_side:
                            video_final_side = obter_video_catalogo(modalidade_aluno, nome_final)

                        novo_treino = {
                            "exercicio": nome_final,
                            "series": int(series),
                            "reps": reps.strip() if reps.strip() else "10 a 12",
                            "url_video": video_final_side,
                            "observacoes": observacoes.strip()
                        }
                        st.session_state.db[aluno_atual].setdefault("treinos", []).append(novo_treino)
                        atualizar_db()
                        notificar_sucesso(f"Exercício '{nome_final}' salvo!", "💾")
                        st.success(f"Exercício '{nome_final}' adicionado com sucesso!")
                        st.rerun()
        else:
            st.info("👈 Selecione um atleta acima para adicionar exercícios à ficha dele.")
    else:
        st.markdown("#### ⚡ Meu Treino")
        aluno_atual = aluno_atribuido
        if aluno_atual not in st.session_state.db:
            aluno_atual = None
        if aluno_atual:
            modalidade_aluno = st.session_state.db[aluno_atual].get("modalidade", "Treino")
            st.markdown(f"Modalidade: **{MODALIDADES_ICONES.get(modalidade_aluno, modalidade_aluno)}**")
            total_ex = len(st.session_state.db[aluno_atual].get("treinos", []))
            st.caption(f"Total de exercícios na ficha: **{total_ex}**")

# ==========================================
# ÁREA PRINCIPAL
# ==========================================

# 1. SE NENHUM ALUNO ESTIVER SELECIONADO
if not aluno_atual:
    if eh_admin:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, rgba(21, 29, 47, 0.78) 0%, rgba(13, 19, 32, 0.84) 100%), url('data:image/jpeg;base64,{LOGO_BASE64 or ""}') center center / contain no-repeat; background-color: #0b1120; border: 1px solid rgba(245, 196, 0, 0.28); border-radius: 24px; padding: 2rem 1.8rem; margin-bottom: 1.5rem; text-align: center;">
                <span class="kn-chip" style="margin-bottom: 0.8rem;">⚡ PAINEL DO TREINADOR</span>
                <h1 style="margin: 0.3rem 0; font-size: 2.3rem;">Treino bem planejado. Evolução constante.</h1>
                <p style="color: #94a3b8; font-size: 1.05rem; max-width: 720px; margin: 0 auto;">
                    Estruture treinos específicos, monitore a presença e acompanhe a evolução de cada atleta.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        total_alunos = len(st.session_state.db)
        total_treinos_cadastrados = sum(len(dados.get("treinos", [])) for dados in st.session_state.db.values())
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Atletas Cadastrados", total_alunos)
        c2.metric("Exercícios no Banco", total_treinos_cadastrados)
        c3.metric("Modalidades Ativas", len(MODALIDADES_EXERCICIOS))

        tab_home_atletas, tab_home_videos_adm = st.tabs([
            "👥 Gerenciar Atletas & Planos de Treino",
            "🎥 Gravar & Adicionar Vídeos dos Exercícios (Somente Admin)",
        ])

        with tab_home_atletas:
            st.info("👈 Selecione um atleta abaixo para visualizar ou adicionar exercícios ao plano de treino.")

            if total_alunos > 0:
                with st.container(border=True):
                    st.markdown("#### ⚡ Seleção Rápida de Atleta")
                    st.caption("Escolha o atleta abaixo para abrir e montar o treino imediatamente:")
                    c_sel_rap, c_btn_rap = st.columns([3, 1], vertical_alignment="bottom")
                    with c_sel_rap:
                        atleta_rapido_home = st.selectbox(
                            "Selecione o Atleta:",
                            alunos_existentes,
                            key="sb_home_quick_select",
                            format_func=lambda a: f"⚡ {a} ({MODALIDADES_ICONES.get(st.session_state.db[a].get('modalidade'), st.session_state.db[a].get('modalidade', 'Esporte'))}) • {len(st.session_state.db[a].get('treinos', []))} exercícios cadastrados"
                        )
                    with c_btn_rap:
                        if st.button("🏋️ Abrir / Montar Treino", type="primary", key="btn_home_quick_open", use_container_width=True):
                            st.session_state["aluno_selecionado"] = atleta_rapido_home
                            st.session_state["sb_aluno_ver"] = st.session_state.get("sb_aluno_ver", 0) + 1
                            st.rerun()

            with st.expander("➕ Cadastrar Novo Atleta", expanded=(total_alunos == 0)):
                with st.form("form_cadastrar_aluno_painel"):
                    c_nom, c_mod = st.columns([1.5, 1])
                    with c_nom:
                        dash_novo_nome = st.text_input("Nome Completo do Atleta", placeholder="Ex.: Lucas Lima", key="txt_dash_novo_aluno")
                    with c_mod:
                        dash_nova_mod = st.selectbox(
                            "Modalidade Principal",
                            list(MODALIDADES_EXERCICIOS.keys()),
                            format_func=lambda m: MODALIDADES_ICONES.get(m, m),
                            key="sb_dash_nova_mod"
                        )
                    if st.form_submit_button("Cadastrar e Montar Treino", type="primary", use_container_width=True):
                        nome_limpo = dash_novo_nome.strip()
                        if nome_limpo and nome_limpo not in st.session_state.db:
                            st.session_state.db[nome_limpo] = {
                                "modalidade": dash_nova_mod,
                                "treinos": []
                            }
                            atualizar_db()
                            st.session_state["aluno_selecionado"] = nome_limpo
                            st.session_state["sb_aluno_ver"] = st.session_state.get("sb_aluno_ver", 0) + 1
                            st.success(f"Atleta {nome_limpo} cadastrado com sucesso!")
                            st.rerun()
                        elif nome_limpo in st.session_state.db:
                            st.error("Este atleta já está cadastrado!")
                        else:
                            st.error("Informe o nome do atleta.")

            if total_alunos > 0:
                st.markdown("### 📋 Atletas Ativos")
                cols_alunos = st.columns(min(3, max(1, total_alunos)))
                for idx, (nome_al, dados_al) in enumerate(st.session_state.db.items()):
                    col_target = cols_alunos[idx % len(cols_alunos)]
                    with col_target:
                        with st.container(border=True):
                            st.markdown(f"#### ⚡ {nome_al}")
                            mod = dados_al.get('modalidade', 'Esporte')
                            st.caption(f"Modalidade: **{MODALIDADES_ICONES.get(mod, mod)}**")
                            n_exercicios = len(dados_al.get('treinos', []))
                            st.markdown(f"<span class='kn-chip-cyan'>{n_exercicios} exercícios cadastrados</span>", unsafe_allow_html=True)
                            st.write("")
                            if st.button(f"🏋️ Abrir / Montar Treino", key=f"btn_dash_open_{nome_al}", type="primary", use_container_width=True):
                                st.session_state["aluno_selecionado"] = nome_al
                                st.session_state["sb_aluno_ver"] = st.session_state.get("sb_aluno_ver", 0) + 1
                                st.rerun()

        with tab_home_videos_adm:
            renderizar_central_videos_admin(aluno_contexto=None, sufixo="home")
    else:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, rgba(21, 29, 47, 0.78) 0%, rgba(13, 19, 32, 0.84) 100%), url('data:image/jpeg;base64,{LOGO_BASE64 or ""}') center center / contain no-repeat; background-color: #0b1120; border: 1px solid rgba(245, 196, 0, 0.28); border-radius: 24px; padding: 2rem 1.8rem; margin-bottom: 1.5rem; text-align: center;">
                <span class="kn-chip" style="margin-bottom: 0.8rem;">⚡ MEU TREINO</span>
                <h1 style="margin: 0.3rem 0; font-size: 2.3rem;">Olá, {usuario_autenticado} 👋</h1>
                <p style="color: #94a3b8; font-size: 1.05rem; margin: 0;">
                    Seu treino personalizado está sendo preparado pelo treinador.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info("Assim que seu treinador liberar sua planilha, seus exercícios e vídeos aparecerão aqui.")

else:
    # 2. ATLETA SELECIONADO: BARRA DE NAVEGAÇÃO SUPERIOR + FOTO DO ATLETA EM CIMA DE TUDO E DADOS DO ATLETA EM BAIXO
    if eh_admin:
        with st.container(border=True):
            c_sel_topo, c_btn_novo, c_btn_todos = st.columns([2.5, 1, 1], vertical_alignment="bottom")
            with c_sel_topo:
                opcoes_atletas = alunos_existentes
                idx_sel = opcoes_atletas.index(aluno_atual) if aluno_atual in opcoes_atletas else 0
                aluno_topo_escolhido = st.selectbox(
                    "👤 Atleta em Edição (Troque de Atleta Aqui):",
                    opcoes_atletas,
                    index=idx_sel,
                    key=f"sb_topo_selecao_atleta_{st.session_state.get('sb_aluno_ver', 0)}",
                    format_func=lambda a: f"⚡ {a} ({MODALIDADES_ICONES.get(st.session_state.db.get(a, {}).get('modalidade'), st.session_state.db.get(a, {}).get('modalidade', 'Esporte'))}) • {len(st.session_state.db.get(a, {}).get('treinos', []))} ex."
                )
                if aluno_topo_escolhido != aluno_atual:
                    st.session_state["aluno_selecionado"] = aluno_topo_escolhido
                    st.session_state["sb_aluno_ver"] = st.session_state.get("sb_aluno_ver", 0) + 1
                    st.rerun()
            with c_btn_novo:
                if st.button("➕ Novo Atleta", key="btn_topo_novo_atleta", use_container_width=True):
                    st.session_state["aluno_selecionado"] = None
                    st.session_state["sb_aluno_ver"] = st.session_state.get("sb_aluno_ver", 0) + 1
                    st.rerun()
            with c_btn_todos:
                if st.button("👥 Ver Todos", key="btn_topo_ver_todos", use_container_width=True):
                    st.session_state["aluno_selecionado"] = None
                    st.session_state["sb_aluno_ver"] = st.session_state.get("sb_aluno_ver", 0) + 1
                    st.rerun()

    dados_aluno = st.session_state.db[aluno_atual]
    treinos = dados_aluno.get("treinos", [])
    modalidade = dados_aluno.get("modalidade", "Treinamento")
    modalidade_formatada = MODALIDADES_ICONES.get(modalidade, modalidade)

    # Recupera os dados de perfil completos do atleta
    perfil_atleta = obter_perfil_atleta(aluno_atual, usuarios)
    peso_val = perfil_atleta.get("peso_kg") if perfil_atleta.get("peso_kg") is not None else perfil_atleta.get("peso")
    altura_val = perfil_atleta.get("altura_cm") if perfil_atleta.get("altura_cm") is not None else perfil_atleta.get("altura")
    idade_val = perfil_atleta.get("idade")
    sexo_val = perfil_atleta.get("sexo", "Não informado")
    foto_val = perfil_atleta.get("foto") or perfil_atleta.get("foto_base64")

    try:
        peso_num = float(peso_val) if peso_val is not None else None
    except (ValueError, TypeError):
        peso_num = None

    try:
        altura_num = float(altura_val) if altura_val is not None else None
    except (ValueError, TypeError):
        altura_num = None

    try:
        idade_num = int(idade_val) if idade_val is not None else None
    except (ValueError, TypeError):
        idade_num = None

    imc_num = calcular_imc(peso_num, altura_num)
    classificacao_imc = "Normal"
    if imc_num is not None:
        if imc_num < 18.5:
            classificacao_imc = "Abaixo do peso"
        elif imc_num < 25:
            classificacao_imc = "Peso ideal"
        elif imc_num < 30:
            classificacao_imc = "Sobrepeso"
        else:
            classificacao_imc = "Obesidade"

    # Prepara a imagem para o st.image de forma segura
    foto_para_exibir = None
    if foto_val and isinstance(foto_val, str):
        if foto_val.startswith("data:image"):
            try:
                raw_b64 = foto_val.split("base64,", 1)[1]
                foto_para_exibir = Image.open(BytesIO(base64.b64decode(raw_b64)))
            except Exception:
                foto_para_exibir = None
        else:
            try:
                foto_para_exibir = Image.open(BytesIO(base64.b64decode(foto_val)))
            except Exception:
                foto_para_exibir = None

    # --- 1. FOTO DO ATLETA EM CIMA DE TUDO ---
    col_e, col_foto_centro, col_d = st.columns([1, 0.8, 1])
    with col_foto_centro:
        if foto_para_exibir is not None:
            with st.container():
                st.markdown('<div class="kn-photo-frame">', unsafe_allow_html=True)
                st.image(foto_para_exibir, width=150)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                """
                <div style="display: flex; justify-content: center;">
                    <div class="kn-athlete-placeholder">👤</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # --- 2. EM BAIXO OS DADOS DO ATLETA ---
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h1 style="margin: 0.2rem 0 0.4rem; font-size: 2.3rem; color: #ffffff;">{aluno_atual}</h1>
            <div style="display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-bottom: 0.8rem;">
                <span class="kn-chip-cyan">{modalidade_formatada}</span>
                <span class="kn-chip">⚡ Atleta Ativo</span>
            </div>
            <div class="kn-data-grid">
                <div class="kn-data-card">
                    <div class="kn-data-label">⚖️ Peso</div>
                    <div class="kn-data-value">{f"{peso_num:.1f} kg" if peso_num else "--"}</div>
                </div>
                <div class="kn-data-card">
                    <div class="kn-data-label">📏 Altura</div>
                    <div class="kn-data-value">{f"{altura_num:.1f} cm" if altura_num else "--"}</div>
                </div>
                <div class="kn-data-card">
                    <div class="kn-data-label">🎂 Idade</div>
                    <div class="kn-data-value">{f"{idade_num} anos" if idade_num else "--"}</div>
                </div>
                <div class="kn-data-card">
                    <div class="kn-data-label">⚡ IMC</div>
                    <div class="kn-data-value" style="color: #f5c400;">{f"{imc_num:.1f}" if imc_num else "--"}</div>
                    <div style="font-size: 0.72rem; color: #38bdf8; font-weight: 700; margin-top: 2px;">{classificacao_imc if imc_num else ""}</div>
                </div>
                <div class="kn-data-card">
                    <div class="kn-data-label">⚧️ Gênero</div>
                    <div class="kn-data-value" style="font-size: 1rem; padding-top: 3px;">{sexo_val}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Expander retrátil para atualizar foto e dados
    with st.expander(f"⚙️ Atualizar Foto e Dados Corporais de {aluno_atual}", expanded=False):
        col_ed_foto, col_ed_dados = st.columns([1, 2], gap="large")

        with col_ed_foto:
            if foto_para_exibir is not None:
                st.image(foto_para_exibir, width=130, caption=f"Foto Atual de {aluno_atual}")
            else:
                st.caption("Sem foto cadastrada no momento.")

            foto_nova = st.file_uploader(
                "Selecionar Nova Foto",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"upload_foto_{aluno_atual}",
                help="Tamanho máximo recomendado: 300KB"
            )
            remover_foto_atual = st.checkbox("Remover foto", key=f"rem_foto_{aluno_atual}") if foto_para_exibir is not None else False

        with col_ed_dados:
            c_p, c_a = st.columns(2)
            peso_edit = c_p.number_input(
                "Peso (kg)",
                min_value=1.0,
                max_value=350.0,
                value=peso_num if peso_num is not None else 70.0,
                step=0.1,
                format="%.1f",
                key=f"input_peso_{aluno_atual}"
            )
            altura_edit = c_a.number_input(
                "Altura (cm)",
                min_value=50.0,
                max_value=250.0,
                value=altura_num if altura_num is not None else 170.0,
                step=0.5,
                format="%.1f",
                key=f"input_altura_{aluno_atual}"
            )

            c_i, c_s = st.columns(2)
            idade_edit = c_i.number_input(
                "Idade (anos)",
                min_value=1,
                max_value=120,
                value=idade_num if idade_num is not None else 20,
                step=1,
                key=f"input_idade_{aluno_atual}"
            )
            opcoes_genero = ["Não informado", "Feminino", "Masculino", "Outro", "Prefiro não informar"]
            idx_gen = opcoes_genero.index(sexo_val) if sexo_val in opcoes_genero else 0
            sexo_edit = c_s.selectbox(
                "Gênero",
                opcoes_genero,
                index=idx_gen,
                key=f"input_sexo_{aluno_atual}"
            )

            if st.button("Salvar Dados e Foto do Atleta", type="primary", use_container_width=True):
                novo_perfil = {
                    "peso": peso_edit,
                    "peso_kg": peso_edit,
                    "altura": altura_edit,
                    "altura_cm": altura_edit,
                    "idade": idade_edit,
                    "sexo": sexo_edit,
                }
                try:
                    if foto_nova is not None:
                        foto_processada = preparar_foto_perfil(foto_nova)
                        novo_perfil["foto"] = foto_processada
                        novo_perfil["foto_base64"] = foto_processada
                    elif foto_val and not remover_foto_atual:
                        novo_perfil["foto"] = foto_val
                        novo_perfil["foto_base64"] = foto_val
                except Exception as erro:
                    st.error(f"Erro ao salvar foto: {erro}")
                else:
                    if aluno_atual in st.session_state.db:
                        st.session_state.db[aluno_atual]["perfil"] = novo_perfil
                        if eh_admin:
                            atualizar_db()

                    for u_nome, u_reg in usuarios.items():
                        if u_reg.get("aluno") == aluno_atual or u_nome.casefold() == aluno_atual.casefold():
                            u_reg["perfil"] = novo_perfil
                            salvar_usuarios(usuarios)
                            break

                    st.success("Dados do atleta atualizados com sucesso!")
                    st.rerun()

    # --- EXCLUIR ALUNO + BLOQUEAR ACESSO (somente admin) ---
    if eh_admin and aluno_atual:
        with st.expander("🚫 Excluir aluno e bloquear acesso", expanded=False):
            contas_do_aluno = [
                u_nome for u_nome, u_reg in usuarios.items()
                if not eh_administrador(u_nome) and (
                    u_reg.get("aluno") == aluno_atual or u_nome.casefold() == aluno_atual.casefold()
                )
            ]
            st.warning(
                f"Isso apaga **{aluno_atual}** com todos os treinos e remove o login "
                + (f"({', '.join(contas_do_aluno)}) " if contas_do_aluno else "")
                + "— ele não conseguirá mais entrar no aplicativo."
            )
            chave_conf_total = f"confirmar_excluir_total_{aluno_atual}"
            if st.button("🗑️ Excluir aluno", use_container_width=True, key=f"btn_excluir_total_{aluno_atual}"):
                st.session_state[chave_conf_total] = True
            if st.session_state.get(chave_conf_total):
                st.error(f"Tem certeza que quer excluir **{aluno_atual}**? Não dá para desfazer.")
                c_tot_sim, c_tot_nao = st.columns(2)
                with c_tot_nao:
                    if st.button("Cancelar", use_container_width=True, key=f"btn_excluir_total_nao_{aluno_atual}"):
                        st.session_state.pop(chave_conf_total, None)
                        st.rerun()
                with c_tot_sim:
                    confirmado = st.button("Sim, excluir", type="primary", use_container_width=True,
                                           key=f"btn_excluir_total_sim_{aluno_atual}")
                if confirmado:
                    nome_removido = aluno_atual
                    erros_exclusao, logins_removidos = excluir_aluno_total(
                        conta_dados, nome_removido, st.session_state.db
                    )
                    st.session_state.pop(chave_conf_total, None)
                    st.session_state["aluno_selecionado"] = None
                    st.session_state["sb_aluno_ver"] = st.session_state.get("sb_aluno_ver", 0) + 1
                    if erros_exclusao:
                        st.session_state["aviso_exclusao"] = "Alguns itens não foram removidos: " + " | ".join(erros_exclusao)
                    else:
                        notificar_sucesso(f"{nome_removido} excluído e acesso bloqueado!", "🚫")
                    st.rerun()

    # --- MÉTRICAS DE TREINO DO ATLETA (KPIS) ---
    catalogo_atual = obter_catalogo_sessao()
    total_series = sum(t.get("series", 0) for t in treinos)
    total_videos = sum(
        bool(t.get("url_video") or obter_video_catalogo(modalidade, t.get("exercicio", ""), catalogo_atual))
        for t in treinos
    )
    faltas = dados_aluno.get("faltas", [])

    if eh_admin:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Exercícios", len(treinos))
        m2.metric("Séries Totais", total_series)
        m3.metric("Vídeos de Apoio", total_videos)
        m4.metric("Faltas Registradas", len(faltas))

        tab_treino, tab_videos_adm, tab_frequencia, tab_analise = st.tabs(
            [
                "📋 Plano de Treino",
                "🎥 Gravar & Adicionar Vídeos (Somente Admin)",
                "📅 Frequência & Presença",
                "📈 Análise de Volume",
            ]
        )
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Exercícios", len(treinos))
        m2.metric("Séries Totais", total_series)
        m3.metric("Vídeos de Apoio", total_videos)

        tab_treino, tab_analise = st.tabs(["📋 Meu Treino", "📈 Análise de Volume"])

    # ==========================================
    # TAB 1: FICHA DE TREINO
    # ==========================================
    with tab_treino:
        if eh_admin:
            lista_exercicios_sug = obter_exercicios_modalidade(modalidade, catalogo_atual)

            # --- BARRA SUPERIOR DE SALVAMENTO & STATUS DO TREINO ---
            with st.container(border=True):
                col_info_salvar, col_btn_salvar = st.columns([2.5, 1.5], vertical_alignment="center")
                with col_info_salvar:
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 2rem;">⚡</span>
                            <div>
                                <h4 style="margin: 0; color: #ffffff;">Plano de Treino • {aluno_atual}</h4>
                                <span style="font-size: 0.88rem; color: #94a3b8;">
                                    {len(treinos)} exercício{'s' if len(treinos) != 1 else ''} • {modalidade_formatada} • <strong style="color: #10b981;">Tudo Salvo</strong>
                                </span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                with col_btn_salvar:
                    if st.button("💾 Salvar Treino no Sistema", type="primary", key=f"btn_salvar_treino_topo_{aluno_atual}", use_container_width=True):
                        atualizar_db()
                        notificar_sucesso(f"Treino de {aluno_atual} salvo com sucesso!", "💾")
                        st.success(f"✅ Treino de {aluno_atual} salvo com sucesso!")

            st.write("")

            # --- PAINEL FÁCIL PARA O TREINADOR ADICIONAR EXERCÍCIOS ---
            with st.container(border=True):
                st.markdown(f"#### ➕ Montar Treino de {aluno_atual}")
                st.caption("Escolha o jeito mais fácil para montar ou adicionar exercícios:")

                aba_rapida, aba_detalhada, aba_copiar = st.tabs([
                    "🚀 Seleção Rápida em Lote (Mais Fácil)",
                    "✏️ Adicionar Exercício Detalhado",
                    "📋 Copiar Treino de Outro Atleta"
                ])

                # 1. ABA RÁPIDA: SELEÇÃO EM LOTE
                with aba_rapida:
                    st.markdown(f"**Marque os exercícios desejados de {modalidade_formatada}:**")
                    ex_selecionados = st.multiselect(
                        "Exercícios Recomendados",
                        lista_exercicios_sug,
                        key=f"multi_ex_rapidos_{aluno_atual}",
                        placeholder="Clique para marcar 1 ou mais exercícios...",
                        help="Você pode marcar vários exercícios de uma só vez e adicioná-los com 1 clique!"
                    )

                    c_s_rap, c_r_rap = st.columns(2)
                    with c_s_rap:
                        series_rap = c_s_rap.number_input("Séries padrão", min_value=1, max_value=30, value=3, step=1, key=f"num_s_rap_{aluno_atual}")
                    with c_r_rap:
                        reps_rap = c_r_rap.text_input("Reps ou Tempo padrão", value="10 a 12", key=f"txt_r_rap_{aluno_atual}")

                    c_btn_lote, c_btn_todos = st.columns([1.5, 1])
                    with c_btn_lote:
                        if st.button("⚡ Adicionar Exercícios Marcados", type="primary", key=f"btn_add_lote_{aluno_atual}", use_container_width=True):
                            if not ex_selecionados:
                                st.warning("Selecione pelo menos um exercício na lista acima para adicionar.")
                            else:
                                for ex_nome in ex_selecionados:
                                    st.session_state.db[aluno_atual].setdefault("treinos", []).append({
                                        "exercicio": ex_nome,
                                        "series": int(series_rap),
                                        "reps": reps_rap.strip() if reps_rap.strip() else "10 a 12",
                                        "url_video": obter_video_catalogo(modalidade, ex_nome, catalogo_atual),
                                        "observacoes": ""
                                    })
                                atualizar_db()
                                notificar_sucesso(f"{len(ex_selecionados)} exercícios adicionados e salvos!", "✅")
                                st.success(f"{len(ex_selecionados)} exercícios adicionados e salvos na ficha de {aluno_atual}!")
                                st.rerun()

                    with c_btn_todos:
                        if st.button(f"🌟 Adicionar Todos de {modalidade}", key=f"btn_add_all_{aluno_atual}", use_container_width=True, help="Adiciona todos os exercícios base da modalidade de uma vez só"):
                            for ex_nome in lista_exercicios_sug:
                                st.session_state.db[aluno_atual].setdefault("treinos", []).append({
                                    "exercicio": ex_nome,
                                    "series": 3,
                                    "reps": "10 a 12",
                                    "url_video": obter_video_catalogo(modalidade, ex_nome, catalogo_atual),
                                    "observacoes": ""
                                })
                            atualizar_db()
                            notificar_sucesso(f"Todos os exercícios de {modalidade} foram adicionados!", "🌟")
                            st.rerun()

                # 2. ABA DETALHADA: FORMULÁRIO COM VÍDEO E OBSERVAÇÕES
                with aba_detalhada:
                    with st.form(f"form_add_treino_detalhado_{aluno_atual}"):
                        c_ex_sug, c_ex_dig = st.columns([1.2, 1], gap="medium")
                        with c_ex_sug:
                            ex_sugerido = st.selectbox(
                                "Exercício Sugerido da Modalidade",
                                lista_exercicios_sug + ["+ Outro exercício personalizado"],
                                key=f"main_sel_ex_{aluno_atual}"
                            )
                        with c_ex_dig:
                            ex_personalizado = st.text_input(
                                "Ou Digite Outro Exercício",
                                placeholder="Deixe em branco para usar o sugerido",
                                key=f"main_txt_ex_{aluno_atual}"
                            )

                        c_set, c_rep = st.columns(2, gap="medium")
                        with c_set:
                            num_series = st.number_input(
                                "Número de Séries",
                                min_value=1,
                                max_value=30,
                                value=3,
                                step=1,
                                key=f"main_series_{aluno_atual}"
                            )
                        with c_rep:
                            txt_reps = st.text_input(
                                "Volume / Repetições ou Tempo",
                                value="10 a 12",
                                placeholder="Ex: 10 a 12 reps, 45 seg, até a falha",
                                key=f"main_reps_{aluno_atual}"
                            )

                        txt_video = st.text_input(
                            "URL do Vídeo Demonstrativo (YouTube / Link)",
                            placeholder="https://www.youtube.com/watch?v=...",
                            key=f"main_video_{aluno_atual}"
                        )
                        arq_video_det = st.file_uploader(
                            "Ou Enviar / Gravar Arquivo de Vídeo do Aparelho (MP4, MOV, WEBM)",
                            type=["mp4", "mov", "webm", "avi", "mkv", "m4v", "3gp"],
                            key=f"main_file_video_{aluno_atual}",
                            help="No celular, toque aqui para abrir a Câmera/Filmadora ou escolher da Galeria."
                        )
                        txt_obs = st.text_area(
                            "Orientações Técnicas / Dicas do Treinador",
                            placeholder="Ex: Manter tronco firme, foco na postura e na velocidade de reação...",
                            key=f"main_obs_{aluno_atual}"
                        )

                        btn_salvar_treino_det = st.form_submit_button(
                            "➕ Adicionar e Salvar Exercício",
                            type="primary",
                            use_container_width=True
                        )

                        if btn_salvar_treino_det:
                            nome_exercicio_final = ex_personalizado.strip() if ex_personalizado.strip() else (
                                ex_sugerido if ex_sugerido != "+ Outro exercício personalizado" else ""
                            )
                            if not nome_exercicio_final:
                                st.error("Informe o nome do exercício para adicionar.")
                            else:
                                video_det_final = txt_video.strip()
                                if arq_video_det is not None:
                                    try:
                                        video_det_final = salvar_arquivo_video_upload(arq_video_det, f"{modalidade}_{nome_exercicio_final}")
                                        salvar_video_em_catalogo_e_atletas(modalidade, nome_exercicio_final, video_det_final, salvar_catalogo=True)
                                    except Exception as err_vd:
                                        st.error(f"Erro ao salvar arquivo de vídeo: {err_vd}")
                                elif not video_det_final:
                                    video_det_final = obter_video_catalogo(modalidade, nome_exercicio_final, catalogo_atual)

                                novo_treino = {
                                    "exercicio": nome_exercicio_final,
                                    "series": int(num_series),
                                    "reps": txt_reps.strip() if txt_reps.strip() else "10 a 12",
                                    "url_video": video_det_final,
                                    "observacoes": txt_obs.strip()
                                }
                                st.session_state.db[aluno_atual].setdefault("treinos", []).append(novo_treino)
                                atualizar_db()
                                notificar_sucesso(f"Exercício '{nome_exercicio_final}' salvo!", "💾")
                                st.success(f"Exercício '{nome_exercicio_final}' adicionado e salvo com sucesso!")
                                st.rerun()

                # 3. ABA COPIAR TREINO DE OUTRO ATLETA
                with aba_copiar:
                    outros_atletas = [
                        a for a in alunos_existentes 
                        if a != aluno_atual and len(st.session_state.db.get(a, {}).get("treinos", [])) > 0
                    ]
                    if not outros_atletas:
                        st.info("Nenhum outro atleta possui exercícios cadastrados para copiar no momento.")
                    else:
                        st.markdown("**Copie rapidamente o treino de outro atleta:**")
                        c_atleta_orig, c_modo_orig = st.columns(2)
                        with c_atleta_orig:
                            atleta_origem = st.selectbox(
                                "Copiar treino de:",
                                outros_atletas,
                                format_func=lambda a: f"⚡ {a} ({len(st.session_state.db[a].get('treinos', []))} exercícios)",
                                key=f"sb_copiar_origem_{aluno_atual}"
                            )
                        with c_modo_orig:
                            modo_copia = st.radio(
                                "Opção de Cópia:",
                                ["Adicionar aos já existentes", "Substituir treino atual"],
                                key=f"rd_modo_copia_{aluno_atual}"
                            )

                        if st.button("📋 Confirmar e Copiar Treino", type="primary", key=f"btn_copiar_treino_{aluno_atual}", use_container_width=True):
                            treinos_copiados = [dict(t) for t in st.session_state.db[atleta_origem].get("treinos", [])]
                            if modo_copia == "Substituir treino atual":
                                st.session_state.db[aluno_atual]["treinos"] = treinos_copiados
                            else:
                                st.session_state.db[aluno_atual].setdefault("treinos", []).extend(treinos_copiados)
                            atualizar_db()
                            notificar_sucesso(f"Treino de {atleta_origem} copiado para {aluno_atual}!", "📋")
                            st.success(f"Foram copiados {len(treinos_copiados)} exercícios de {atleta_origem} para {aluno_atual} com sucesso!")
                            st.rerun()

            st.write("")

        if not treinos:
            st.markdown(
                f"""
                <div class="kn-empty-video" style="padding: 3rem 1.5rem;">
                    <span style="font-size: 2.8rem;">📋</span>
                    <h3 style="margin: 0; color: #ffffff;">Ficha de treino vazia</h3>
                    <p style="color: #94a3b8; margin: 0; max-width: 480px;">
                        {'Utilize o painel acima para adicionar exercícios rapidamente à ficha de ' + aluno_atual + '.' if eh_admin else 'Nenhum exercício cadastrado ainda. Seu treinador em breve liberará sua rotina.'}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            for i, treino in enumerate(treinos):
                nome_exercicio = treino.get('exercicio', 'Exercício')
                series = treino.get('series', 3)
                reps = treino.get('reps', '10 a 12')
                obs = treino.get('observacoes', '').strip()
                url_video = treino.get('url_video', '').strip()
                video_efetivo = url_video or obter_video_catalogo(modalidade, nome_exercicio, catalogo_atual)

                titulo_expander = f"⚡ {i+1}. {nome_exercicio}  •  {series} Séries  •  {reps}"
                with st.expander(titulo_expander, expanded=True):
                    col_detalhes, col_midia = st.columns([1.1, 1], gap="large")
                    
                    with col_detalhes:
                        st.markdown(
                            f"""
                            <div style="display: flex; gap: 12px; margin-bottom: 12px; flex-wrap: wrap;">
                                <div class="kn-stat-badge">
                                    <span style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Séries</span>
                                    <span style="font-size: 1.35rem; font-weight: 800; color: #f5c400;">{series}</span>
                                </div>
                                <div class="kn-stat-badge">
                                    <span style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Volume / Reps</span>
                                    <span style="font-size: 1.35rem; font-weight: 800; color: #ffffff;">{reps}</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        if obs:
                            st.markdown(
                                f"""
                                <div class="kn-coach-note">
                                    <strong style="color: #f5c400;">💡 Instrução Técnica:</strong><br>
                                    {obs}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        if eh_admin:
                            st.write("")
                            # Barra de ações rápidas: Mover Cima, Mover Baixo, Duplicar, Editar, Excluir
                            cols_acoes = st.columns([0.8, 0.8, 1.2, 1, 1])
                            with cols_acoes[0]:
                                if st.button("⬆️", key=f"up_{aluno_atual}_{i}", help="Mover exercício para cima", use_container_width=True, disabled=(i == 0)):
                                    st.session_state.db[aluno_atual]["treinos"][i], st.session_state.db[aluno_atual]["treinos"][i-1] = (
                                        st.session_state.db[aluno_atual]["treinos"][i-1], st.session_state.db[aluno_atual]["treinos"][i]
                                    )
                                    atualizar_db()
                                    st.rerun()
                            with cols_acoes[1]:
                                if st.button("⬇️", key=f"down_{aluno_atual}_{i}", help="Mover exercício para baixo", use_container_width=True, disabled=(i == len(treinos) - 1)):
                                    st.session_state.db[aluno_atual]["treinos"][i], st.session_state.db[aluno_atual]["treinos"][i+1] = (
                                        st.session_state.db[aluno_atual]["treinos"][i+1], st.session_state.db[aluno_atual]["treinos"][i]
                                    )
                                    atualizar_db()
                                    st.rerun()
                            with cols_acoes[2]:
                                if st.button("📋 Duplicar", key=f"dup_{aluno_atual}_{i}", help="Duplicar este exercício", use_container_width=True):
                                    copia_ex = dict(treino)
                                    st.session_state.db[aluno_atual]["treinos"].insert(i + 1, copia_ex)
                                    atualizar_db()
                                    notificar_sucesso("Exercício duplicado e salvo!", "📋")
                                    st.rerun()
                            with cols_acoes[3]:
                                edit_open = st.checkbox("✏️ Editar", key=f"check_edit_{aluno_atual}_{i}")
                            with cols_acoes[4]:
                                if st.button("🗑️ Remover", key=f"del_{aluno_atual}_{i}", help="Excluir este exercício do plano", use_container_width=True):
                                    st.session_state.db[aluno_atual]["treinos"].pop(i)
                                    atualizar_db()
                                    notificar_sucesso("Exercício removido!", "🗑️")
                                    st.rerun()

                            if edit_open:
                                with st.form(f"form_quick_edit_{aluno_atual}_{i}"):
                                    ed_nome = st.text_input("Nome do Exercício", value=nome_exercicio, key=f"ed_nome_{aluno_atual}_{i}")
                                    c_es, c_er = st.columns(2)
                                    ed_series = c_es.number_input("Séries", min_value=1, max_value=30, value=int(series), step=1, key=f"ed_s_{aluno_atual}_{i}")
                                    ed_reps = c_er.text_input("Reps/Tempo", value=str(reps), key=f"ed_r_{aluno_atual}_{i}")
                                    ed_video = st.text_input(
                                        "URL do Vídeo (YouTube / Link)",
                                        value="" if url_video.startswith("arquivo_local:") else url_video,
                                        key=f"ed_v_{aluno_atual}_{i}"
                                    )
                                    ed_arq_video = st.file_uploader(
                                        "Ou Enviar/Gravar Novo Arquivo de Vídeo",
                                        type=["mp4", "mov", "webm", "avi", "mkv", "m4v", "3gp"],
                                        key=f"ed_file_v_{aluno_atual}_{i}"
                                    )
                                    ed_obs = st.text_area("Orientações", value=obs, key=f"ed_o_{aluno_atual}_{i}")
                                    if st.form_submit_button("Salvar Alterações", type="primary", use_container_width=True):
                                        nome_ed_final = ed_nome.strip() if ed_nome.strip() else nome_exercicio
                                        vid_ed_final = ed_video.strip() if ed_video.strip() else url_video
                                        if ed_arq_video is not None:
                                            try:
                                                vid_ed_final = salvar_arquivo_video_upload(ed_arq_video, f"{modalidade}_{nome_ed_final}")
                                            except Exception as err_ed_v:
                                                st.error(f"Erro ao salvar vídeo: {err_ed_v}")
                                        st.session_state.db[aluno_atual]["treinos"][i] = {
                                            "exercicio": nome_ed_final,
                                            "series": int(ed_series),
                                            "reps": ed_reps.strip(),
                                            "url_video": vid_ed_final,
                                            "observacoes": ed_obs.strip()
                                        }
                                        atualizar_db()
                                        notificar_sucesso("Exercício atualizado e salvo!", "💾")
                                        st.success("Exercício atualizado com sucesso!")
                                        st.rerun()

                    with col_midia:
                        if video_efetivo:
                            st.markdown("<span style='font-size: 0.85rem; font-weight: 700; color: #cbd5e1;'>🎥 DEMONSTRAÇÃO EM VÍDEO</span>", unsafe_allow_html=True)
                            exibir_player_video(video_efetivo)
                        else:
                            st.markdown(
                                """
                                <div class="kn-empty-video">
                                    <span style="font-size: 2rem;">🎬</span>
                                    <span style="color: #64748b; font-size: 0.88rem;">Sem vídeo demonstrativo associado</span>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        if eh_admin:
                            slug_in_al = re.sub(r"[^a-z0-9]+", "_", str(aluno_atual).lower()).strip("_")
                            chave_in_card = f"inline_{slug_in_al}_{i}"
                            with st.expander("🎥 Gravar ou Colocar Vídeo neste Exercício (Admin)", expanded=False):
                                with st.container(key=f"box_up_vid_{chave_in_card}"):
                                    up_in = st.file_uploader(
                                        "📁 Enviar Vídeo ou Gravar pelo Celular/PC",
                                        type=["mp4", "mov", "webm", "avi", "mkv", "m4v", "3gp"],
                                        key=f"file_up_vid_{chave_in_card}",
                                        help="No celular, toque aqui para filmar com a câmera ou escolher da galeria."
                                    )
                                link_in = st.text_input(
                                    "🔗 Ou Link do Vídeo (YouTube / MP4)",
                                    value="" if video_efetivo.startswith("arquivo_local:") else video_efetivo,
                                    placeholder="https://www.youtube.com/watch?v=...",
                                    key=f"lnk_in_{chave_in_card}"
                                )
                                cam_in = st.checkbox("📷 Abrir gravador de câmera ao vivo aqui", key=f"cam_in_{chave_in_card}")
                                if cam_in:
                                    renderizar_gravador_camera_html(chave_in_card, nome_exercicio)

                                c_bi1, c_bi2 = st.columns([2, 1])
                                with c_bi1:
                                    if st.button("💾 Salvar Vídeo", type="primary", use_container_width=True, key=f"btn_sv_in_{chave_in_card}"):
                                        try:
                                            if up_in is not None:
                                                nova_ref_in = salvar_arquivo_video_upload(up_in, f"{modalidade}_{nome_exercicio}")
                                            elif link_in.strip():
                                                nova_ref_in = normalizar_url_video(link_in.strip())
                                            else:
                                                nova_ref_in = ""
                                            if not nova_ref_in:
                                                st.warning("Grave/selecione um vídeo ou informe o link.")
                                            else:
                                                salvar_video_em_catalogo_e_atletas(
                                                    modalidade=modalidade,
                                                    nome_exercicio=nome_exercicio,
                                                    referencia_video=nova_ref_in,
                                                    salvar_catalogo=True,
                                                    atualizar_todos_atletas=False,
                                                    aluno_especifico=aluno_atual,
                                                    indice_treino_especifico=i,
                                                )
                                                notificar_sucesso(f"Vídeo salvo em '{nome_exercicio}'!", "🎥")
                                                st.rerun()
                                        except Exception as err_in:
                                            st.error(f"Erro ao salvar vídeo: {err_in}")
                                with c_bi2:
                                    if video_efetivo:
                                        if st.button("🗑️ Remover", use_container_width=True, key=f"btn_rm_in_{chave_in_card}"):
                                            st.session_state.db[aluno_atual]["treinos"][i]["url_video"] = ""
                                            atualizar_db()
                                            notificar_sucesso("Vídeo removido deste exercício.", "🗑️")
                                            st.rerun()

            if eh_admin and treinos:
                st.write("")
                with st.container(border=True):
                    c_salvar_fim, c_limpar_fim = st.columns([3, 1], vertical_alignment="center")
                    with c_salvar_fim:
                        if st.button("💾 Salvar Treino Completo", type="primary", key=f"btn_salvar_treino_fim_{aluno_atual}", use_container_width=True):
                            atualizar_db()
                            notificar_sucesso(f"Treino de {aluno_atual} salvo com sucesso!", "💾")
                            st.success(f"✅ Treino de {aluno_atual} com {len(treinos)} exercícios está salvo no banco de dados!")
                    with c_limpar_fim:
                        if st.button("🗑️ Limpar Todos", key=f"btn_limpar_treino_{aluno_atual}", help="Apagar todos os exercícios deste treino", use_container_width=True):
                            st.session_state[f"confirm_limpar_{aluno_atual}"] = True

                    if st.session_state.get(f"confirm_limpar_{aluno_atual}"):
                        st.warning(f"Tem certeza que deseja apagar todos os {len(treinos)} exercícios de {aluno_atual}?")
                        c_conf_sim, c_conf_nao = st.columns(2)
                        with c_conf_sim:
                            if st.button("Sim, apagar todos", key=f"btn_conf_limpar_sim_{aluno_atual}", type="primary", use_container_width=True):
                                st.session_state.db[aluno_atual]["treinos"] = []
                                atualizar_db()
                                st.session_state.pop(f"confirm_limpar_{aluno_atual}", None)
                                notificar_sucesso("Treino limpo com sucesso!", "🗑️")
                                st.rerun()
                        with c_conf_nao:
                            if st.button("Cancelar", key=f"btn_conf_limpar_nao_{aluno_atual}", use_container_width=True):
                                st.session_state.pop(f"confirm_limpar_{aluno_atual}", None)
                                st.rerun()

    # ==========================================
    # TAB EXCLUSIVA ADMIN: GRAVAR E ADICIONAR VÍDEOS DOS EXERCÍCIOS
    # ==========================================
    if eh_admin:
        with tab_videos_adm:
            renderizar_central_videos_admin(aluno_contexto=aluno_atual, sufixo="atleta")

    # ==========================================
    # TAB 2: FREQUÊNCIA (APENAS ADMINISTRADOR)
    # ==========================================
    if eh_admin:
        with tab_frequencia:
            faltas = dados_aluno.get("faltas", [])
            mes_atual_str = date.today().strftime("%Y-%m")
            faltas_mes = sum(registro.get("data", "").startswith(mes_atual_str) for registro in faltas)

            rf1, rf2 = st.columns(2)
            rf1.metric("Total de Faltas Registradas", len(faltas))
            rf2.metric("Faltas Neste Mês", faltas_mes)

            st.write("")
            col_cadastrar_falta, col_historico_falta = st.columns([1, 1.3], gap="large")

            with col_cadastrar_falta:
                with st.container(border=True):
                    st.markdown("#### 📝 Registrar Falta")
                    st.caption(f"Controle de presença de **{aluno_atual}** (visível somente ao treinador).")
                    with st.form(f"form_falta_{aluno_atual}"):
                        data_falta = st.date_input("Data da Ausência", value=date.today())
                        motivo_falta = st.text_area(
                            "Motivo ou Observação (Opcional)",
                            placeholder="Ex.: Avisou com antecedência / lesão leve no joelho",
                        )
                        btn_registrar_falta = st.form_submit_button("Registrar Falta", type="primary", use_container_width=True)

                    if btn_registrar_falta:
                        dados_aluno.setdefault("faltas", []).append(
                            {
                                "data": data_falta.isoformat(),
                                "motivo": motivo_falta.strip(),
                            }
                        )
                        atualizar_db()
                        st.success("Falta registrada com sucesso!")
                        st.rerun()

            with col_historico_falta:
                st.markdown("#### 📅 Histórico de Ausências")
                if not faltas:
                    st.markdown(
                        """
                        <div class="kn-success-card">
                            <span style="font-size: 2.2rem;">🏆</span>
                            <div>
                                <h4 style="margin: 0; color: #10b981;">Frequência Impecável!</h4>
                                <p style="margin: 4px 0 0; color: #94a3b8; font-size: 0.9rem;">
                                    Nenhuma falta registrada para este atleta.
                                </p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    for indice, registro in sorted(
                        enumerate(faltas),
                        key=lambda item: item[1].get("data", ""),
                        reverse=True,
                    ):
                        with st.container(border=True):
                            c_data, c_mot, c_del = st.columns([1, 2.2, 0.8], vertical_alignment="center")
                            with c_data:
                                try:
                                    data_formatada = date.fromisoformat(registro['data']).strftime('%d/%m/%Y')
                                except Exception:
                                    data_formatada = registro.get('data', '--')
                                st.markdown(f"**🗓️ {data_formatada}**")
                            with c_mot:
                                st.write(registro.get("motivo") or "Motivo não informado.")
                            with c_del:
                                if st.button("Excluir", key=f"del_falta_{aluno_atual}_{indice}", use_container_width=True):
                                    faltas.pop(indice)
                                    atualizar_db()
                                    st.rerun()

    # ==========================================
    # TAB 3: ANÁLISE DE VOLUME E GRÁFICOS
    # ==========================================
    with tab_analise:
        if not treinos:
            st.info("Cadastre exercícios no plano para visualizar a análise gráfica de volume.")
        else:
            df_treinos = pd.DataFrame(treinos)
            col_g1, col_g2 = st.columns(2, gap="large")

            with col_g1:
                with st.container(border=True):
                    st.markdown("#### 🎯 Distribuição dos Exercícios")
                    st.caption("Proporção de cada fundamento dentro do plano de treino.")
                    fig_donut = plot_distribuicao_exercicios(df_treinos)
                    st.pyplot(fig_donut)

            with col_g2:
                with st.container(border=True):
                    st.markdown("#### ⚡ Volume de Treino (Séries Totais)")
                    st.caption("Carga planejada em número total de séries por exercício.")
                    fig_bar = plot_volume_series(df_treinos)
                    st.pyplot(fig_bar)
