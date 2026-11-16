"""Dependency-free Word export and paginated PDF from the same manuscript blocks."""
import html
import re
import zipfile
import base64
from pathlib import Path
import pymupdf

def blocks(markdown):
    result=[];lines=markdown.splitlines();i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith("!["):
            match=re.fullmatch(r"!\[(.*?)\]\((.*?)\)",line)
            if not match:raise ValueError("Invalid figure markup")
            result.append(("image",match[1],match[2]));i+=1
        elif line.startswith("#"):
            level=len(line)-len(line.lstrip("#"));result.append(("heading",level,line[level:].strip()));i+=1
        elif line.startswith("|"):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith("|"):
                row=[x.strip() for x in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+",v or "-") for v in row):rows.append(row)
                i+=1
            result.append(("table",rows))
        else:
            text=[]
            while i<len(lines) and lines[i].strip() and not lines[i].startswith(("#","|","![")):
                text.append(lines[i].strip());i+=1
            result.append(("paragraph"," ".join(text)))
    return result

def html_document(parts,asset_dir=None):
    content=[]
    for b in parts:
        if b[0]=="heading":content.append(f"<h{b[1]}>{html.escape(b[2])}</h{b[1]}>")
        elif b[0]=="paragraph":content.append("<p>"+html.escape(b[1])+"</p>")
        elif b[0]=="image":
            data=(Path(asset_dir)/b[2]).read_bytes()
            content.append('<p><img style="width:100%" src="data:image/png;base64,'+base64.b64encode(data).decode()+'" alt="'+html.escape(b[1])+'"/></p>')
        else:
            content.append("<table>")
            for i,row in enumerate(b[1]):
                tag="th" if i==0 else "td"
                content.append("<tr>"+"".join(f"<{tag}>{html.escape(v)}</{tag}>" for v in row)+"</tr>")
            content.append("</table>")
    return """<!doctype html><html><head><meta charset="utf-8"><title>CDISCPILOT01 manuscript draft</title>
    <style>body{font-family:serif;font-size:11pt;line-height:1.45;color:#222;max-width:960px;margin:32px auto}
    h1{font-size:20pt}h2{font-size:15pt;margin-top:22px}h3{font-size:12pt;margin-top:16px}
    table{border-collapse:collapse;width:100%;font-size:8pt;margin:12px 0}th,td{border:1px solid #aaa;padding:5px;text-align:left}
    th{background:#eee}p{margin:8px 0}a{overflow-wrap:anywhere}</style></head><body>"""+"".join(content)+"</body></html>"

def pdf_document(text,path,release_ready=False):
    writer=pymupdf.DocumentWriter(str(path))
    story=pymupdf.Story(html=text)
    page=pymupdf.Rect(0,0,595,842);area=pymupdf.Rect(48,46,547,792)
    more=True;n=0
    while more:
        device=writer.begin_page(page);more,_=story.place(area);story.draw(device);writer.end_page();n+=1
        if n>100:raise RuntimeError("Unexpected PDF overflow")
    writer.close()
    doc=pymupdf.open(path)
    for i,p in enumerate(doc):
        p.insert_text((48,817),f"CDISCPILOT01 | {'Manuscript' if release_ready else 'Author-review draft'} | {i+1} / {len(doc)}",fontsize=8,color=(.35,.35,.35))
    temporary=path.with_suffix(".numbered.pdf");doc.save(temporary);doc.close();temporary.replace(path)

def docx_document(parts,path,asset_dir=None):
    def paragraph(text,style=None):
        prop=f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        return f'<w:p>{prop}<w:r><w:t xml:space="preserve">{html.escape(text)}</w:t></w:r></w:p>'
    content=[];images=[]
    for b in parts:
        if b[0]=="heading":content.append(paragraph(b[2],"Title" if b[1]==1 else "Heading"+str(b[1]-1)))
        elif b[0]=="paragraph":content.append(paragraph(b[1]))
        elif b[0]=="image":
            data=(Path(asset_dir)/b[2]).read_bytes();pix=pymupdf.Pixmap(data)
            cx=5943600;cy=int(cx*pix.height/pix.width);rid=f"image{len(images)+1}";images.append((rid,data))
            content.append(f'<w:p><w:r><w:drawing><wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{len(images)}" name="Figure 1"/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="0" name="Figure 1"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
        else:
            cols=len(b[1][0]);width=9360//cols
            content.append('<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="9360" w:type="dxa"/></w:tblPr><w:tblGrid>'+''.join(f'<w:gridCol w:w="{width}"/>' for _ in range(cols))+'</w:tblGrid>')
            for i,row in enumerate(b[1]):
                content.append("<w:tr>"+('<w:trPr><w:tblHeader/></w:trPr>' if i==0 else "")+''.join(f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>'+paragraph(v,"TableText")+"</w:tc>" for v in row)+"</w:tr>")
            content.append("</w:tbl>")
    ns='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    document=f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{ns}"><w:body>'+"".join(content)+'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body></w:document>'
    styles=f'<w:styles xmlns:w="{ns}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="140" w:line="360" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
    for name,size in [("Title",32),("Heading1",28),("Heading2",24),("TableText",18)]:
        styles+=f'<w:style w:type="paragraph" w:styleId="{name}"><w:name w:val="{name}"/><w:pPr><w:keepNext/><w:spacing w:after="120" w:line="260"/></w:pPr><w:rPr>'+('<w:b/>' if name!="TableText" else "")+f'<w:sz w:val="{size}"/></w:rPr></w:style>'
    styles+='<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders>'+''.join(f'<w:{s} w:val="single" w:sz="4" w:color="AAAAAA"/>' for s in ["top","left","bottom","right","insideH","insideV"])+'</w:tblBorders></w:tblPr></w:style></w:styles>'
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="png" ContentType="image/png"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
        z.writestr("_rels/.rels",'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/_rels/document.xml.rels",'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'+''.join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{rid}.png"/>' for rid,_ in images)+'</Relationships>')
        for rid,data in images:z.writestr(f"word/media/{rid}.png",data)
        z.writestr("word/document.xml",document);z.writestr("word/styles.xml",styles)
