# Packages reviewed Spaces slide renders; does not author or modify the live deck.
from reportlab.pdfgen import canvas
from pypdf import PdfReader
from pathlib import Path
import shutil,json,hashlib
root=Path(__file__).resolve().parents[2]
src=root/'docs/presentation/expanded-deck'
dest=root/'docs/presentation/expanded-deck'
dest.mkdir(exist_ok=True)
out=root/'frontend/public/demo/perigee-demo.pdf'
c=canvas.Canvas(str(out),pagesize=(960,540),pageCompression=1)
c.setTitle('Perigee — NASA Space Apps 2026')
c.setAuthor('Sathvik Loke, Sagar Raut, Akshobya Rao, Aditya Raut, Suhrit Bestavemula, Neeraj Movva')
c.setSubject('Seven-slide project demo: SPHEREx investigations, evidence, processing and validation')
md=['# Perigee: seven-slide project demo\n\nUpdated 15 November 2026. This replaces the historical deck.\n\n[Editable presentation](https://chatgpt.com/space/page_c2bdc1167fb481918cc92fabeb2bfc58) · [Public PDF](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf) · [Technical report](https://perigee.lokesathvik.workers.dev/demo/perigee-technical-report.pdf)\n\nThe deck uses Avenir Next, the app’s black/citron palette and original processed NASA/IPAC SPHEREx imagery. Text stays editable in Spaces. The public PDF packages the reviewed 1280×720 renders at 16:9; this preserves the exact layout. The transcript below provides selectable text. Speaker notes in Spaces retain detailed sources and scientific scope.\n']
for i in range(1,8):
 p=src/f'slide-{i}.png'
 layout=json.loads((src/f'slide-{i}.layout.json').read_text())
 md.append(f'\n## Slide {i}\n')
 for e in layout['elements']:
  if e.get('text'):md.append('\n'+e['text']+'\n')
 c.drawImage(str(p),0,0,width=960,height=540)
 if i==7:
  c.linkURL('https://perigee.lokesathvik.workers.dev/?preset=barnards_star',(36,90,900,130),relative=0)
  c.linkURL('https://github.com/sathvikloke/perigee',(36,60,900,87),relative=0)
 c.showPage()
c.save()
assert len(PdfReader(out).pages)==7
(root/'docs/presentation/DECK.md').write_text(''.join(md))
(dest/'verification.json').write_text(json.dumps({'pages':7,'reviewed_render_size':[1280,720],'typeface':'Avenir Next','artifact_page':'page_c2bdc1167fb481918cc92fabeb2bfc58','pdf_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'native_pdf_export':'Unavailable for local Avenir font; public PDF assembled from reviewed live slide renders. Spaces text remains editable.','render_review':'All seven slides inspected; processing column and observation pair repaired and re-rendered.'},indent=2)+'\n')
print(out,len(PdfReader(out).pages),'pages',hashlib.sha256(out.read_bytes()).hexdigest())
