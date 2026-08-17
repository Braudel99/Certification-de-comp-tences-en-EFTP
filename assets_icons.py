"""
assets_icons.py
Icônes SVG inline, sobres et schématiques (pas de photo réaliste — voir échange
précédent sur les limites de génération d'images). Un SVG par compétence,
dimensionné pour tenir dans une card. Couleur unique héritée via currentColor
pour rester cohérent en mode clair et sombre.
"""

ICONE_PV = """
<svg viewBox="0 0 100 100" width="72" height="72" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="15" y="25" width="70" height="45" rx="3" stroke="currentColor" stroke-width="2.5"/>
  <line x1="15" y1="40" x2="85" y2="40" stroke="currentColor" stroke-width="1.5"/>
  <line x1="15" y1="55" x2="85" y2="55" stroke="currentColor" stroke-width="1.5"/>
  <line x1="38" y1="25" x2="38" y2="70" stroke="currentColor" stroke-width="1.5"/>
  <line x1="61" y1="25" x2="61" y2="70" stroke="currentColor" stroke-width="1.5"/>
  <line x1="50" y1="70" x2="50" y2="82" stroke="currentColor" stroke-width="2.5"/>
  <line x1="35" y1="82" x2="65" y2="82" stroke="currentColor" stroke-width="2.5"/>
</svg>
"""

ICONE_CABLAGE = """
<svg viewBox="0 0 100 100" width="72" height="72" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="30" cy="35" r="12" stroke="currentColor" stroke-width="2.5"/>
  <line x1="21" y1="26" x2="39" y2="44" stroke="currentColor" stroke-width="2"/>
  <line x1="39" y1="26" x2="21" y2="44" stroke="currentColor" stroke-width="2"/>
  <rect x="55" y="55" width="24" height="16" rx="2" stroke="currentColor" stroke-width="2.5"/>
  <line x1="55" y1="55" x2="55" y2="71" stroke="currentColor" stroke-width="2"/>
  <line x1="30" y1="47" x2="30" y2="63" stroke="currentColor" stroke-width="1.8"/>
  <line x1="30" y1="63" x2="55" y2="63" stroke="currentColor" stroke-width="1.8"/>
</svg>
"""

ICONE_DIAGNOSTIC = """
<svg viewBox="0 0 100 100" width="72" height="72" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="45" cy="45" r="28" stroke="currentColor" stroke-width="2.5"/>
  <line x1="35" y1="45" x2="55" y2="45" stroke="currentColor" stroke-width="2"/>
  <line x1="45" y1="35" x2="45" y2="45" stroke="currentColor" stroke-width="2"/>
  <line x1="45" y1="45" x2="52" y2="35" stroke="currentColor" stroke-width="2"/>
  <line x1="65" y1="65" x2="82" y2="82" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
</svg>
"""

ICONE_DOMAINE = """
<svg viewBox="0 0 100 100" width="56" height="56" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M52 10 L25 55 H45 L38 90 L75 42 H53 L52 10 Z" stroke="currentColor" stroke-width="3" stroke-linejoin="round" fill="none"/>
</svg>
"""

ICONES = {
    "solaire": ICONE_PV,
    "cablage": ICONE_CABLAGE,
    "diagnostic": ICONE_DIAGNOSTIC,
    "domaine": ICONE_DOMAINE,
}