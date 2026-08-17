"""
theme.py
Bascule clair/sombre par injection CSS (Streamlit ne permet pas de changer son
thème natif à l'exécution). Sombre par défaut ; le toggle en tête de menu
bascule explicitement vers le mode clair.
"""

import streamlit as st

PALETTE_CLAIR = {
    "bg": "#FFFFFF",
    "bg_secondaire": "#F5F5F3",
    "texte": "#1A1A18",
    "texte_secondaire": "#5F5E5A",
    "accent": "#0F6E56",
    "carte_bg": "#FFFFFF",
    "carte_bordure": "#E0DED6",
    "carte_ombre": "rgba(0,0,0,0.08)",
    "carte_ombre_hover": "rgba(0,0,0,0.14)",
}

PALETTE_SOMBRE = {
    "bg": "#161615",
    "bg_secondaire": "#1F1F1D",
    "texte": "#F1EFE8",
    "texte_secondaire": "#B4B2A9",
    "accent": "#5DCAA5",
    "carte_bg": "#232321",
    "carte_bordure": "#3A3A37",
    "carte_ombre": "rgba(0,0,0,0.35)",
    "carte_ombre_hover": "rgba(0,0,0,0.5)",
}


def selecteur_theme():
    """Toggle 'Mode clair' en tête de barre latérale. Sombre par défaut."""
    theme_actuel = st.session_state.get("theme", "sombre")
    clair = st.sidebar.toggle("☀️ Mode clair", value=(theme_actuel == "clair"))
    st.session_state["theme"] = "clair" if clair else "sombre"
    st.sidebar.divider()


def appliquer_theme():
    """Injecte le CSS correspondant au thème actuel. À appeler en haut de chaque page."""
    p = PALETTE_CLAIR if st.session_state.get("theme", "sombre") == "clair" else PALETTE_SOMBRE

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
            background-color: {p['bg']};
        }}
        [data-testid="stSidebar"] {{
            background-color: {p['bg_secondaire']};
        }}
        [data-testid="stAppViewContainer"] * , [data-testid="stSidebar"] * {{
            color: {p['texte']};
        }}

        /* --- Cards de sélection (domaine / compétence) --- */
        .carte {{
            background-color: {p['carte_bg']};
            border: 1px solid {p['carte_bordure']};
            border-radius: 14px;
            overflow: hidden;
            box-shadow: 0 2px 8px {p['carte_ombre']};
            transition: box-shadow 0.15s ease, transform 0.15s ease;
            width: 100%;
            max-width: 320px;
            margin: 0 auto 10px auto;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
        }}
        .carte:hover {{
            box-shadow: 0 6px 16px {p['carte_ombre_hover']};
            transform: translateY(-2px);
        }}
        .carte-image {{
            width: 100%;
            height: 150px;
            object-fit: cover;
            display: block;
        }}
        .carte-icone {{
            width: 100%;
            height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: {p['bg_secondaire']};
            color: {p['accent']};
        }}
        .carte-corps {{
            padding: 14px 16px 18px;
            flex-grow: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .carte-titre {{
            font-size: 15px;
            font-weight: 500;
            line-height: 1.35;
            color: {p['texte']};
            margin: 0;
            text-align: center;
        }}
        div[data-testid="column"] .stButton button {{
            width: 100%;
            max-width: 320px;
            margin: 0 auto;
            display: block;
            box-sizing: border-box;
        }}

        /* --- Adaptation mobile : cartes côte à côte plutôt qu'empilées plein écran --- */
        @media (max-width: 640px) {{
            [data-testid="stHorizontalBlock"] {{
                flex-wrap: nowrap !important;
                gap: 6px !important;
            }}
            [data-testid="column"] {{
                min-width: 0 !important;
                width: auto !important;
                flex: 1 1 0 !important;
            }}
            .carte {{
                max-width: 100%;
            }}
            .carte-image, .carte-icone {{
                height: 72px;
            }}
            .carte-titre {{
                font-size: 11px;
            }}
            div[data-testid="column"] .stButton button {{
                font-size: 11px;
                padding: 4px 6px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )