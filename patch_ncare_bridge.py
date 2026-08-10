#!/usr/bin/env python3
"""Ajoute le pont NcareBridge + un vrai bouton « Terminé » aux modules HTML.

Le bloc injecté est idempotent : relancer le script ne duplique rien, il
remplace le bloc précédent (repéré par les marqueurs NCARE-BRIDGE).
"""

import re
import sys
from pathlib import Path

MODULES_DIR = Path(__file__).resolve().parent
START = "<!-- NCARE-BRIDGE:START -->"
END = "<!-- NCARE-BRIDGE:END -->"

BRIDGE = START + """
<div id="ncare-end" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;background:rgba(10,10,10,0.96);color:#fff;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:32px;">
  <div style="font-size:44px;margin-bottom:16px;">&#10003;</div>
  <div style="font-size:18px;font-weight:700;margin-bottom:8px;">Module termin&eacute;</div>
  <div style="font-size:14px;opacity:0.7;max-width:280px;line-height:1.5;">Vous pouvez fermer cette page et revenir &agrave; l'application.</div>
</div>
<script>
(function(){
  // Envoie un message a l'app Pills (NCare). Retourne false hors de l'app.
  function post(payload){
    try{
      if(window.NcareBridge && window.NcareBridge.postMessage){
        window.NcareBridge.postMessage(JSON.stringify(payload));
        return true;
      }
    }catch(e){}
    return false;
  }

  // Remonte la progression a chaque changement de slide, sans modifier
  // la fonction navigate() d'origine.
  var inner = window.navigate;
  window.navigate = function(dir){
    inner(dir);
    post({event:'progress', slide: window.current + 1, total: window.total});
  };

  // Derniere slide : « Termine ». Ferme la page et revient dans l'app.
  window.finishModule = function(){
    if(post({event:'completed', slide: window.total, total: window.total})) return;
    // Hors de l'app : le navigateur ignore souvent window.close(),
    // on affiche alors un ecran de fin.
    window.close();
    setTimeout(function(){
      if(document.hidden) return;
      var el = document.getElementById('ncare-end');
      if(el) el.style.display = 'flex';
    }, 300);
  };

  window.onNext = function(){
    if(window.current === window.total - 1) return window.finishModule();
    window.navigate(1);
  };

  post({event:'ready', slide: window.current + 1, total: window.total});
})();
</script>
""" + END


def patch(path: Path) -> str:
    html = path.read_text(encoding="utf-8")
    original = html

    # 1. Le bouton de la derniere slide doit appeler onNext(), pas navigate(1).
    html, n = re.subn(
        r'(id="nextBtn"[^>]*?onclick=")navigate\(1\)(")',
        r"\1onNext()\2",
        html,
    )

    # 2. (Re)injection du pont juste avant </body>.
    html = re.sub(
        re.escape(START) + r".*?" + re.escape(END) + r"\s*",
        "",
        html,
        flags=re.DOTALL,
    )
    if "</body>" not in html:
        return "PAS DE </body>"
    html = html.replace("</body>", BRIDGE + "\n</body>", 1)

    if html == original:
        return "inchange"
    path.write_text(html, encoding="utf-8")
    return f"ok (bouton patche: {n})"


def main() -> int:
    files = sorted(MODULES_DIR.glob("Ncare_*.html"))
    if not files:
        print("Aucun module trouve", file=sys.stderr)
        return 1
    for f in files:
        print(f"{f.name}: {patch(f)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
