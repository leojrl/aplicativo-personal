import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import json
import os
import base64
import hashlib
import hmac
import secrets
from datetime import date
from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError

# ==========================================
# CONFIGURAÇÕES E DADOS BASE
# ==========================================
st.set_page_config(
    page_title="KN Alta Performance",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

DIRETORIO_APP = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(DIRETORIO_APP, "dados_treinos.json")
ARQUIVO_USUARIOS = os.path.join(DIRETORIO_APP, "usuarios.json")
CAMINHO_LOGO = os.path.join(DIRETORIO_APP, "1000370127.jpg")
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

# Somente Leo e Wilian são administradores. Todos os demais são alunos/atletas.
ADMINS_AUTORIZADOS = {"leo", "wilian", "willian"}

def eh_administrador(nome_usuario):
    """Retorna True ESTRITAMENTE para os administradores autorizados: Leo e Wilian."""
    if not nome_usuario or not isinstance(nome_usuario, str):
        return False
    return nome_usuario.strip().lower() in ADMINS_AUTORIZADOS

def injetar_css(codigo_css):
    """Injeta código CSS com compatibilidade universal para todas as versões do Streamlit."""
    try:
        if hasattr(st, "html"):
            st.html(f"<style>\n{codigo_css}\n</style>")
        else:
            st.markdown(f"<style>\n{codigo_css}\n</style>", unsafe_allow_html=True)
    except Exception:
        st.markdown(f"<style>\n{codigo_css}\n</style>", unsafe_allow_html=True)

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
    if not caminho or not os.path.isfile(caminho):
        return None
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
        return None

def obter_caminho_foto_login():
    candidatos = [
        "foto_login.jpg",
        "foto_login.png",
        "foto_login.jpeg",
        "fundo_login.jpg",
        "fundo_login.png",
        "fundo_login.jpeg",
        "login_bg.jpg",
        "login_bg.png",
        "1000370127.jpg",
    ]
    for nome in candidatos:
        caminho = os.path.join(DIRETORIO_APP, nome)
        if os.path.isfile(caminho):
            return caminho
    return CAMINHO_LOGO if os.path.isfile(CAMINHO_LOGO) else None

LOGO_BASE64 = carregar_imagem_base64(CAMINHO_LOGO, (512, 512), 85)
FUNDO_LOGO_B64 = carregar_imagem_base64(CAMINHO_LOGO, (800, 800), 75)

def injetar_fundo_dashboard():
    if FUNDO_LOGO_B64:
        injetar_css(
            f"""
            [data-testid="stAppViewContainer"] {{
                background-color: #070b13 !important;
                background-image: 
                    radial-gradient(circle at 50% 50%, rgba(10, 15, 26, 0.65) 0%, rgba(7, 10, 18, 0.82) 65%, rgba(5, 7, 13, 0.94) 100%),
                    url('data:image/jpeg;base64,{FUNDO_LOGO_B64}') !important;
                background-position: center center, center center !important;
                background-repeat: no-repeat, no-repeat !important;
                background-attachment: fixed, fixed !important;
                background-size: cover, min(750px, 85vmin) !important;
            }}
            section.main, [data-testid="stMain"], [data-testid="stMainBlockContainer"] {{
                background: transparent !important;
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
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 50% -10%, #172338 0%, #0a0e17 65%, #05070c 100%) fixed;
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
    contas_alvo = ["leo", "wilian"] if eh_administrador(usuario) else [usuario]
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
                    # Garante que os documentos pais de ambos os admins (leo e wilian) existam e fiquem sincronizados na nuvem
                    if eh_administrador(usuario):
                        for adm_c in ["leo", "wilian"]:
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
                        for conta_ref in contas_alvo:
                            d_local["contas"][conta_ref] = alunos
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
    # REGRA ESTREITA: Somente Leo e Wilian são administradores. Todos os outros são alunos/usuários.
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
        raise PermissionError("Acesso negado: Somente os administradores (Leo e Wilian) podem alterar treinos.")

    contas_alvo = ["leo", "wilian"] if eh_administrador(usuario) else [usuario]
    if usuario and usuario not in contas_alvo:
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
        contas = {adm: {} for adm in ["leo", "wilian"]}
        dados = {"versao": 2, "contas": contas}

    for conta_ref in contas_alvo:
        dados["contas"][conta_ref] = dados_usuario
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
                apenas_locais = [n for n in usuarios if n not in nuvem]
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
            "wilian": {
                "salt": "4314dae8bc86258615cbd9885d5a8f1a",
                "hash": "16dd48325f790d2047a3c46fe234fa035f0391b82413b20869a69cb502f975d0",
                "tipo": "admin"
            }
        }
        try:
            salvar_usuarios(usuarios)
        except Exception:
            pass

    # REGRA: SOMENTE LEO E WILIAN SÃO ADMINS. TODOS OS OUTROS SÃO USUÁRIOS/ALUNOS.
    alterado = False
    for u_nome, u_reg in usuarios.items():
        if eh_administrador(u_nome):
            if u_reg.get("tipo") != "admin":
                u_reg["tipo"] = "admin"
                alterado = True
        else:
            if u_reg.get("tipo") != "usuario":
                u_reg["tipo"] = "usuario"
                alterado = True

    # Garante que leo e wilian sempre existam no sistema com credenciais válidas e tipo "admin"
    if "leo" not in usuarios:
        usuarios["leo"] = {
            "salt": "6016dac021652a820a05d5fe89d3c36f",
            "hash": "8ad3c1f5fb334d592435e0bdcfad76836e9860b948683e8d1bac5a4414742d47",
            "tipo": "admin"
        }
        alterado = True
    if "wilian" not in usuarios or usuarios["wilian"].get("salt") == "9f2b8c7e1d4a5b6c3e2f1a0b9c8d7e6f":
        perfil_wilian = usuarios.get("wilian", {}).get("perfil") if isinstance(usuarios.get("wilian"), dict) else None
        usuarios["wilian"] = {
            "salt": "4314dae8bc86258615cbd9885d5a8f1a",
            "hash": "16dd48325f790d2047a3c46fe234fa035f0391b82413b20869a69cb502f975d0",
            "tipo": "admin"
        }
        if perfil_wilian:
            usuarios["wilian"]["perfil"] = perfil_wilian
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
    foto_b64 = carregar_imagem_base64(caminho_foto, (1920, 1920), 85)

    if foto_b64:
        estilo_fundo_tela_toda = f"""
        /* FUNDO DA TELA TODA DE LOGIN COM A FOTO EM TELA CHEIA */
        html, body, .stApp,
        [data-testid="stAppViewContainer"] {{
            background-color: #05070c !important;
            background-image: 
                linear-gradient(rgba(5, 7, 13, 0.40), rgba(5, 7, 13, 0.70)),
                url('data:image/jpeg;base64,{foto_b64}') !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
            background-size: cover !important;
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
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"] {{
            background: transparent !important;
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

        /* Card de login branco com borda e sombra (opaco: nada aparece atrás das letras) */
        .st-key-card_login_box {{
            background-color: #ffffff !important;
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

        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 1.2rem; margin-top: 0.4rem;">
                <span style="display: inline-block; background: #f5c400; color: #000000; border-radius: 20px; padding: 5px 16px; font-size: 0.82rem; font-weight: 800; letter-spacing: 0.05em; margin-bottom: 0.6rem;">
                    ⚡ KN ALTA PERFORMANCE
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
                usuario_alvo = "wilian" if usuario == "willian" and "willian" not in usuarios else usuario
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
            st.caption("A nova conta será de atleta/aluno. Somente Leo e Wilian são administradores.")
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
                        "tipo": "usuario",  # SOMENTE LEO E WILIAN SÃO ADMINS
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
registro_usuario = usuarios.get(usuario_autenticado)
if not registro_usuario:
    limpar_sessao_url()
    st.session_state.pop("usuario_autenticado", None)
    st.stop()

# Garante que o token de sessão esteja gravado na URL do navegador para futuros recarregamentos
token_atual = obter_sessao_url()
if not token_atual or validar_token_sessao(token_atual, usuarios) != usuario_autenticado:
    definir_sessao_url(gerar_token_sessao(usuario_autenticado, registro_usuario))

# SOMENTE LEO E WILIAN SÃO ADMINISTRADORES
eh_admin = eh_administrador(usuario_autenticado)
contas_admin = [adm for adm in ["leo", "wilian"] if adm in usuarios]
if not contas_admin:
    contas_admin = ["leo", "wilian"]
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

if st.session_state.get("aviso_exclusao"):
    st.error(st.session_state.pop("aviso_exclusao"))

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    if os.path.exists(CAMINHO_LOGO):
        st.image(CAMINHO_LOGO, width=220)
    else:
        st.markdown("### ⚡ KN ALTA PERFORMANCE")

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
            st.caption("Controle de acessos do sistema. **Somente Leo e Wilian são administradores.**")
            
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

            lista_exercicios = MODALIDADES_EXERCICIOS.get(modalidade_aluno, [])
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
                observacoes = st.text_area("Orientações / Observações", placeholder="Ex: Manter tronco firme, foco na explosão...", key=f"side_txt_obs_{aluno_atual}")

                btn_add_side = st.form_submit_button("Adicionar ao Treino", type="primary", use_container_width=True)
                if btn_add_side:
                    nome_final = exercicio_customizado.strip() if exercicio_customizado.strip() else (
                        exercicio_selecionado if exercicio_selecionado != opcao_personalizada else ""
                    )
                    if not nome_final:
                        st.error("Digite ou selecione o nome do exercício.")
                    else:
                        novo_treino = {
                            "exercicio": nome_final,
                            "series": int(series),
                            "reps": reps.strip() if reps.strip() else "10 a 12",
                            "url_video": url_video.strip(),
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
            """
            <div style="background: linear-gradient(135deg, rgba(21, 29, 47, 0.95) 0%, rgba(13, 19, 32, 0.95) 100%); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 24px; padding: 2rem 1.8rem; margin-bottom: 1.5rem; text-align: center;">
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
    else:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, rgba(21, 29, 47, 0.95) 0%, rgba(13, 19, 32, 0.95) 100%); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 24px; padding: 2rem 1.8rem; margin-bottom: 1.5rem; text-align: center;">
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
    total_series = sum(t.get("series", 0) for t in treinos)
    total_videos = sum(bool(t.get("url_video")) for t in treinos)
    faltas = dados_aluno.get("faltas", [])

    if eh_admin:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Exercícios", len(treinos))
        m2.metric("Séries Totais", total_series)
        m3.metric("Vídeos de Apoio", total_videos)
        m4.metric("Faltas Registradas", len(faltas))

        tab_treino, tab_frequencia, tab_analise = st.tabs(
            ["📋 Plano de Treino", "📅 Frequência & Presença", "📈 Análise de Volume"]
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
            lista_exercicios_sug = MODALIDADES_EXERCICIOS.get(modalidade, [])

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
                                        "url_video": "",
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
                                    "url_video": "",
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
                            "URL do Vídeo Demonstrativo (YouTube)",
                            placeholder="https://www.youtube.com/watch?v=...",
                            key=f"main_video_{aluno_atual}"
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
                                novo_treino = {
                                    "exercicio": nome_exercicio_final,
                                    "series": int(num_series),
                                    "reps": txt_reps.strip() if txt_reps.strip() else "10 a 12",
                                    "url_video": txt_video.strip(),
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
                                    ed_video = st.text_input("URL do Vídeo", value=url_video, key=f"ed_v_{aluno_atual}_{i}")
                                    ed_obs = st.text_area("Orientações", value=obs, key=f"ed_o_{aluno_atual}_{i}")
                                    if st.form_submit_button("Salvar Alterações", type="primary", use_container_width=True):
                                        st.session_state.db[aluno_atual]["treinos"][i] = {
                                            "exercicio": ed_nome.strip() if ed_nome.strip() else nome_exercicio,
                                            "series": int(ed_series),
                                            "reps": ed_reps.strip(),
                                            "url_video": ed_video.strip(),
                                            "observacoes": ed_obs.strip()
                                        }
                                        atualizar_db()
                                        notificar_sucesso("Exercício atualizado e salvo!", "💾")
                                        st.success("Exercício atualizado com sucesso!")
                                        st.rerun()

                    with col_midia:
                        if url_video:
                            st.markdown("<span style='font-size: 0.85rem; font-weight: 700; color: #cbd5e1;'>🎥 DEMONSTRAÇÃO EM VÍDEO</span>", unsafe_allow_html=True)
                            url_video_ok = normalizar_url_video(url_video)
                            try:
                                st.video(url_video_ok)
                            except Exception:
                                st.warning("Não foi possível reproduzir o vídeo. Verifique se o link é válido.")
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
