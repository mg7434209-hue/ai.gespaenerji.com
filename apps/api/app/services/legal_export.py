"""Dilekçe taslağını Word (.docx) dosyasına çevirir.

Ek bağımlılık yok: .docx bir zip + OOXML'dir, stdlib zipfile ile üretilir.
Markdown benzeri girdiyi (başlık, kalın, madde) biçimli paragraflara döker.
"""
import io
import re
import zipfile
from datetime import datetime

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

# Times New Roman 12pt — dilekçe teamülü
STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
<w:sz w:val="24"/><w:szCs w:val="24"/><w:lang w:val="tr-TR"/>
</w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault>
</w:docDefaults>
</w:styles>"""


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _runs(text: str) -> str:
    """**kalın** parçalarını ayrı run'lara böler."""
    out = []
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if not part:
            continue
        bold = "<w:rPr><w:b/></w:rPr>" if i % 2 == 1 else ""
        out.append(
            f'<w:r>{bold}<w:t xml:space="preserve">{_esc(part)}</w:t></w:r>'
        )
    return "".join(out) or '<w:r><w:t xml:space="preserve"></w:t></w:r>'


def _para(text: str, *, bold=False, center=False, size=None, space_before=0) -> str:
    props = []
    if center:
        props.append('<w:jc w:val="center"/>')
    if space_before:
        props.append(f'<w:spacing w:before="{space_before}" w:after="120"/>')
    ppr = f"<w:pPr>{''.join(props)}</w:pPr>" if props else ""
    if bold or size:
        rpr = "<w:rPr>" + ("<w:b/>" if bold else "") + (f'<w:sz w:val="{size}"/>' if size else "") + "</w:rPr>"
        body = f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(text)}</w:t></w:r>'
    else:
        body = _runs(text)
    return f"<w:p>{ppr}{body}</w:p>"


def _body(text: str) -> str:
    """Markdown benzeri metni paragraflara çevirir."""
    paras = []
    for raw in (text or "").split("\n"):
        line = raw.rstrip()
        if not line.strip():
            paras.append("<w:p/>")
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            paras.append(_para(heading[2], bold=True, size=26, space_before=200))
            continue
        bullet = re.match(r"^\s*[-*]\s+(.*)$", line)
        if bullet:
            paras.append(_para(f"•  {bullet[1]}"))
            continue
        # Dilekçe başlıkları ortalanır
        stripped = line.strip()
        if stripped.isupper() and 3 < len(stripped) < 90:
            paras.append(_para(stripped, bold=True, center=True))
            continue
        paras.append(_para(line))
    return "".join(paras)


def build_docx(title: str, content: str, footer_note: str = "") -> bytes:
    """Tek parçalı .docx üretir ve baytlarını döner."""
    parts = []
    if title:
        parts.append(_para(title.upper(), bold=True, center=True, size=28))
        parts.append("<w:p/>")
    parts.append(_body(content))
    if footer_note:
        parts.append("<w:p/>")
        parts.append(_para("— " + footer_note, size=18))

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(parts)}"
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1701"/></w:sectPr>'
        "</w:body></w:document>"
    )
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{_esc(title or 'Dilekçe')}</dc:title>"
        "<dc:creator>Gespa OS Hukuk Ofisi</dc:creator>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</dcterms:created>'
        "</cp:coreProperties>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/document.xml", document)
        z.writestr("docProps/core.xml", core)
    return buf.getvalue()


def safe_filename(name: str, ext: str) -> str:
    """Türkçe karakterleri sadeleştirip güvenli dosya adı üretir."""
    table = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    base = (name or "belge").translate(table)
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-") or "belge"
    return f"{base[:80]}.{ext}"
