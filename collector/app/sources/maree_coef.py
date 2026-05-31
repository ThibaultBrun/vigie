import re
import requests

URL = "https://maree.info/{}"
JOURS = "Lun|Mar|Mer|Jeu|Ven|Sam|Dim"


def coefficients(port_id):
    r = requests.get(URL.format(port_id), timeout=25, headers={"User-Agent": "Mozilla/5.0 (vigie)"})
    r.raise_for_status()
    html = r.text
    md = re.search(r"'Dates'\s*:\s*\[([0-9,]+)\]", html)
    if not md:
        return None
    dates = [int(x) for x in md.group(1).split(",")]
    txt = re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ")
    i = txt.find("Coeff")
    if i >= 0:
        txt = txt[i:i + 1500]
    txt = re.sub(r"\s+", " ", txt)
    blocs = re.split(rf"(?=(?:{JOURS})\.)", txt)
    rows = []
    for b in blocs:
        mb = re.match(rf"(?:{JOURS})\.\s*\d{{1,2}}\b(.*)", b)
        if not mb:
            continue
        toks = mb.group(1).split()
        coefs = [int(t) for t in toks if re.fullmatch(r"\d{2,3}", t) and 20 <= int(t) <= 120]
        rows.append(coefs[:2])
    out = []
    for idx, ymd in enumerate(dates):
        c = rows[idx] if idx < len(rows) else []
        out.append({"date": f"{ymd // 10000:04d}-{(ymd // 100) % 100:02d}-{ymd % 100:02d}", "coefficients": c})
    return out
