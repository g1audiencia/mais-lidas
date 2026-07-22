# -*- coding: utf-8 -*-
"""
Coleta as 5 mais lidas de 11 portais e salva em dados.json.
Roda no GitHub Actions (de hora em hora). Nada é instalado localmente.
"""
import requests, json, datetime, re
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
MAX_ITENS = 5

def coletor_folha(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    bloco = soup.find("div", class_="c-most-read")
    if bloco is None: raise ValueError("bloco 'c-most-read' não encontrado")
    lista = bloco.find("ol", class_="c-most-read__list")
    if lista is None: raise ValueError("lista não encontrada")
    itens = []
    for i, li in enumerate(lista.find_all("li"), start=1):
        a = li.find("a")
        if not a or not a.get("href"): continue
        url = a["href"].strip()
        strong = a.find("strong")
        if strong: strong.extract()
        itens.append({"rank": i, "title": a.get_text(separator=" ", strip=True), "url": url})
    return itens

def coletor_uol(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    bloco = soup.find("section", class_="mostRead")
    if bloco is None: raise ValueError("bloco 'mostRead' não encontrado")
    lista = bloco.find("ol", class_="mostRead__list")
    if lista is None: raise ValueError("lista não encontrada")
    itens = []
    for i, li in enumerate(lista.find_all("li"), start=1):
        a = li.find("a")
        if not a or not a.get("href"): continue
        h3 = a.find("h3")
        titulo = h3.get_text(strip=True) if h3 else a.get("title","").strip()
        itens.append({"rank": i, "title": titulo, "url": a["href"].strip()})
    return itens

def coletor_cnn(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    bloco = soup.find(attrs={"aria-label": re.compile(r"mais\s*lidas", re.I)})
    if bloco is None: raise ValueError("região 'Mais Lidas' não encontrada")
    PREFIXO = re.compile(r"^\s*Imagem representando a matéria:\s*", re.I)
    itens = []; vistos = set()
    for a in bloco.find_all("a"):
        al = a.get("aria-label",""); href = a.get("href","")
        if not al or not href or not PREFIXO.search(al) or href in vistos: continue
        vistos.add(href)
        span = a.find("span", string=re.compile(r"^\d+$"))
        rank = int(span.get_text(strip=True)) if span else len(itens)+1
        itens.append({"rank": rank, "title": PREFIXO.sub("", al).strip(), "url": href})
    itens.sort(key=lambda x: x["rank"])
    for i, it in enumerate(itens, 1): it["rank"] = i
    return itens

def coletor_oglobo(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    h4 = None
    for h in soup.find_all("h4"):
        if re.search(r"Mais\s*Lidas", h.get_text(), re.I): h4 = h; break
    if h4 is None: raise ValueError("título 'Mais Lidas' não encontrado")
    section = h4.find_parent("section", class_="card")
    if section is None: raise ValueError("section não encontrada")
    itens = []; vistos = set()
    for a in section.find_all("a"):
        href = a.get("href","").strip().split("#")[0]
        titulo = a.get_text(" ", strip=True)
        if not href or not titulo or href in vistos: continue
        vistos.add(href)
        itens.append({"rank": len(itens)+1, "title": titulo, "url": href})
    return itens

def coletor_estadao(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    bloco = soup.find("div", class_="container-lista-mais-lidas") or soup.find(id="container-lista-mais-lidas")
    if bloco is None: raise ValueError("bloco 'Preferidas dos assinantes' não encontrado")
    itens = []; vistos = set()
    for a in bloco.find_all("a"):
        href = a.get("href","").strip(); titulo = a.get_text(" ", strip=True)
        if not href or not titulo or href in vistos: continue
        if href.startswith("/"): href = "https://www.estadao.com.br" + href
        titulo = re.sub(r"^\s*\d+\s*\.\s*", "", titulo)
        vistos.add(href)
        itens.append({"rank": len(itens)+1, "title": titulo, "url": href})
    return itens

def coletor_metropoles(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    itens_div = soup.find_all("div", class_=re.compile(r"mtp-mais-lidas-noticia-\d+"))
    if not itens_div: raise ValueError("bloco do Metrópoles não encontrado")
    itens = []
    for div in itens_div:
        a_titulo = div.find("a", attrs={"cmp-ltrk-idx": "1"})
        if a_titulo is None:
            h4 = div.find("h4"); a_titulo = h4.find("a") if h4 else None
        if a_titulo is None: continue
        href = a_titulo.get("data-mrf-link") or a_titulo.get("href","")
        if href.startswith("/"): href = "https://www.metropoles.com" + href
        itens.append({"rank": len(itens)+1, "title": a_titulo.get_text(" ", strip=True), "url": href})
    return itens

def coletor_r7(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    header = None
    for t in soup.find_all(string=re.compile("mais lida", re.I)): header = t.parent; break
    if header is None: raise ValueError("header 'mais lidas' do R7 não encontrado")
    section = header.find_parent("section")
    if section is None: raise ValueError("section do R7 não encontrada")
    itens = []; vistos = set()
    for o in section.find_all(attrs={"data-order": True}):
        a = o.find("a") or o.find_parent("a")
        if a is None: continue
        href = a.get("href","").strip()
        h4 = o.find("h4")
        titulo = h4.get_text(" ", strip=True) if h4 else o.get_text(" ", strip=True)
        if not href or not titulo or href in vistos: continue
        vistos.add(href)
        try: rank = int(o.get("data-order"))
        except: rank = len(itens)+1
        itens.append({"rank": rank, "title": titulo, "url": href})
    itens.sort(key=lambda x: x["rank"])
    for i, it in enumerate(itens, 1): it["rank"] = i
    return itens

def coletor_ap(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    bloco = soup.find(attrs={"data-gtm-region": re.compile("most read", re.I)})
    if bloco is None: raise ValueError("bloco 'Most read' do AP não encontrado")
    itens = []; vistos = set()
    for a in bloco.find_all("a"):
        href = a.get("href","").strip(); titulo = a.get_text(" ", strip=True)
        if not href or not titulo or href in vistos: continue
        vistos.add(href)
        itens.append({"rank": len(itens)+1, "title": titulo, "url": href})
    return itens


def coletor_bbc(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    h2_mr = None
    for h in soup.find_all(["h2","h3"]):
        if re.search(r"most read", h.get_text(), re.I):
            h2_mr = h; break
    bloco = None
    if h2_mr:
        bloco = h2_mr.find_parent("section") or h2_mr.find_parent("div")
    if bloco is None:
        melhor=None; n=0
        for sec in soup.find_all(["section","ol","div"]):
            la = sec.find_all("a", href=re.compile(r"/news/articles/"))
            if len(la)>n and len(la)<=12:
                n=len(la); melhor=sec
        bloco = melhor
    if bloco is None:
        raise ValueError("bloco 'Most read' da BBC nao encontrado")
    itens=[]; vistos=set()
    for a in bloco.find_all("a", href=re.compile(r"/news/articles/")):
        href=a.get("href","").strip()
        if href.startswith("/"): href="https://www.bbc.com"+href
        h2=a.find(["h2","h3"])
        if h2:
            titulo=h2.get_text(" ",strip=True)
        else:
            titulo=re.sub(r"^\s*\d+\s+","",a.get_text(" ",strip=True))
        if not titulo or href in vistos: continue
        vistos.add(href)
        itens.append({"rank":len(itens)+1,"title":titulo,"url":href})
    return itens

def coletor_clarin(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    links = soup.find_all("a", href=re.compile(r"^/.*\.html"))
    itens = []; vistos = set()
    for a in links:
        titulo = a.get("aria-label","").strip()
        href = a.get("data-mrf-link") or a.get("href","")
        if href.startswith("/"): href = "https://www.clarin.com" + href
        # excluir galerias de foto e vídeos que se infiltram na lista
        if "/fotogalerias/" in href or "/videos/" in href: continue
        # só considerar links que estão no bloco "Lo más visto" (têm aria-label real)
        if not titulo or not href or href in vistos: continue
        vistos.add(href)
        pai = a.parent
        num = pai.find("span", class_="number") if pai else None
        try: rank = int(num.get_text(strip=True)) if num else len(itens)+1
        except: rank = len(itens)+1
        itens.append({"rank": rank, "title": titulo, "url": href})
    itens.sort(key=lambda x: x["rank"])
    for i, it in enumerate(itens, 1): it["rank"] = i
    return itens

PORTAIS = [
    ("Folha",      "https://www.folha.uol.com.br/",    coletor_folha,      5),
    ("UOL",        "https://www.uol.com.br/",           coletor_uol,        5),
    ("CNN Brasil", "https://www.cnnbrasil.com.br/",     coletor_cnn,        5),
    ("O Globo",    "https://oglobo.globo.com/",         coletor_oglobo,     5),
    ("Estadão",    "https://www.estadao.com.br/",       coletor_estadao,    5),
    ("Metrópoles", "https://www.metropoles.com/",       coletor_metropoles, 3),
    ("R7",         "https://www.r7.com/",               coletor_r7,         5),
    ("AP",         "https://apnews.com/",               coletor_ap,         3),
    ("BBC News",   "https://www.bbc.com/news",          coletor_bbc,        5),
    ("Clarín",     "https://www.clarin.com/",           coletor_clarin,     3),
]

def coletar():
    resultados = []
    for nome, url, func, minimo in PORTAIS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=25)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            itens = func(resp.text)
            if len(itens) < minimo:
                raise ValueError(f"esperava ao menos {minimo} itens, achei {len(itens)}")
            itens = itens[:MAX_ITENS]
            for i, it in enumerate(itens, 1): it["rank"] = i
            resultados.append({"portal": nome, "ok": True, "items": itens, "erro": None})
            print(f"[OK]    {nome}: {len(itens)} itens")
        except Exception as e:
            resultados.append({"portal": nome, "ok": False, "items": [], "erro": str(e)})
            print(f"[FALHA] {nome}: {e}")
    return {"atualizado_em": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "portais": resultados}

if __name__ == "__main__":
    dados = coletar()
    with open("dados.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    ok = sum(1 for p in dados["portais"] if p["ok"])
    print(f"\nGravado dados.json — {ok}/{len(dados['portais'])} portais OK")
