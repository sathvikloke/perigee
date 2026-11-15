// Live Artifact Session callback. Execute with its prebound presentation, never as a standalone deck builder.
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const C={bg:'#080A0A',text:'#F5F6F5',muted:'#AFB6BA',accent:'#D7FC70',line:'#343B3B',panel:'#141919'};
function text(s,t,x,y,w,h,size=23,color=C.text,bold=false){const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=t;a.text.style={fontSize:size,typeface:'Avenir Next',color,bold,autoFit:'none',wrap:'square',insets:0};return a;}
function line(s,x,y,w,color=C.line){s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:1},fill:color,line:{fill:'none',width:0}});}
function img(s,path,x,y,w,h,alt){s.images.add({path,alt,position:{left:x,top:y,width:w,height:h},fit:'contain'});}
function link(s,label,url,x,y,w,h,size=20,color=C.accent){const a=text(s,label,x,y,w,h,size,color);a.text.get(label).link={uri:url,isExternal:true};}
function base(s,i,k,title){s.background.fill=C.bg;text(s,`PERIGEE   /   ${k}`,48,26,1140,26,17,C.accent,true);text(s,title,48,65,1184,66,42,C.text,true);line(s,48,678,1184);text(s,'NASA Space Apps 2026 · Planet X and SPHEREx',48,691,1010,19,14,C.muted);text(s,`${i+1} / 7`,1168,689,70,23,16,C.muted);}
function source(s,t){text(s,t,48,649,1184,24,14,C.muted);}
function block(s,head,body,x,y,w,bodyH,size=23){text(s,head,x,y,w,37,26,C.accent,true);text(s,body,x,y+45,w,bodyH,size);}
const paths={ba:root+'/backend/content/presets/barnards_star/case-moving_neighbor/2025W35_1A_0008_1_D3.png',bc:root+'/backend/content/presets/barnards_star/case-moving_neighbor/2026W34_1A_0431_1_D3.png',ea:root+'/backend/content/presets/epsilon_indi_b/case-fair_comparison/2026W18_1A_0516_1_D3.png',ec:root+'/backend/content/presets/epsilon_indi_b/case-fair_comparison/2026W18_1A_0516_1_D6.png',wa:root+'/backend/content/presets/wise_0855/case-wise_0855_quality_trap/2025W45_2A_0278_1_D2.png',wb:root+'/backend/content/presets/wise_0855/case-wise_0855_quality_trap/2025W46_1A_0108_1_D2.png'};
const notes=[
`Sources: https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/ ; https://irsa.ipac.caltech.edu/Missions/spherex.html ; docs/TEAM.md ; docs/SUBMISSION_DRAFT.md. Intended audiences are prospective uses, not recruited or measured users. The deck contains seven slides including this introduction. All six names are confirmed, including Aditya Raut.`,
`Sources: backend/content/cases/moving_neighbor.json; frontend/src/components/CaseBench.tsx; frontend/src/components/Notebook.tsx. Screenshot captured from the published app on 15 November 2026. A/C dates: 25 Aug 2025 and 19 Aug 2026; wavelengths 2.0062 and 2.0284 µm. Catalog A-C displacement: 7.29 display pixels or10.25 arcseconds. The target marker is predicted, the saturated glow is an imprecise visual proxy. Reference is a reflection guide, not automatic grading.`,
`Sources: backend/content/cases/moving_neighbor.json, fair_comparison.json, wise_0855_quality_trap.json; science/reviews/overnight-controls/README.md; science/reviews/transfer-exercise/README.md. Original NASA/IPAC SPHEREx PNGs are unchanged. Epsilon A/C share exposure time but have different detectors, spectral response and stretches. WISE A/B span2.655days; their near-marker dot is not identified as WISE0855. A target quality status does not certify every pixel.`,
`Sources: backend/data/process.py; backend/data/archive.py; backend/platform; https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/ ; https://simbad.cfa.harvard.edu/simbad/ ; https://www.cosmos.esa.int/web/gaia/dr3. Common tangent-plane grid defaults to256px over6arcminutes, north up/east left. Spectral values use WCS-WAVE at predicted detector position. Nearest-neighbor resampling adds no telescope resolution. Shared stretch maps equal physical inputs equally; per-frame limits differ. Live-archive requests retain upstream network dependence.`,
`Sources: science/reviews/acceptance/README.md; science/reviews/registration-audit/README.md and results; science/reviews/overnight-controls/README.md. Historical189-product processing audit =183unique cutouts +6case copies, before third-case packaging; not a census of every current product. Independent unique-cutout verdicts128PASS/55UNKNOWN/0FAIL; including the six copies gives133/56/0. UNKNOWN means fewer than three usable supporting stars. On3selected real-frame fixtures, all injected1/2/5native-pixel shifts were rejected. Thresholds were characterized on retained frames, not a held-out survey benchmark.`,
`Sources: frontend/src/components/Notebook.tsx; science/reviews/contribution/README.md; qa/production-journey; docs/report/TECHNICAL_REPORT.md. Example wording is authored to illustrate the product, not a testimonial. Saved cards hold the latest browser-local state, not revision history or an online class roster. JSON carries machine-readable provenance; print/savePDF creates the shareable human-readable record. Established tools already support image comparison, quality cautions and authored cases; the bounded contribution is the integrated learner-authored reasoning and source record.`,
`Sources: docs/SUBMISSION_DRAFT.md; docs/AI_USE.md; science/reviews/contribution/README.md; official Project Submission Guide read15Nov2026. Educational uses are potential applications. No measured learning-gain, adoption or retention claim. Public PDFs are supporting artifacts. The app runs no AI model; Claude Code and OpenAI Codex assisted implementation and materials. Scientific images are NASA SPHEREx data; generated spacecraft illustrations are not used in these slides. Current live archive search has intermittent upstream timeout failures, documented in qa/landing-motion/RELEASE.md and the technical report; curated investigations are bundled.`];
export async function build({presentation,input}){
 for(const i of input.slides){const old=await presentation.inspect({select:`$.slides[${i}].elements[*]`,include:['id']});if(old.records.length)presentation.delete(old.records.map(x=>x.id));const s=presentation.slides.getItem(i);s.speakerNotes.text=notes[i];
 if(i===0){
  base(s,i,'PROJECT & PURPOSE','');text(s,'Perigee',48,71,710,100,84,C.text,true);text(s,'Investigate change in NASA’s infrared sky',48,181,1130,60,40,C.accent,true);
  text(s,'A free web app for students, teachers and astronomy clubs to compare observations from NASA’s SPHEREx infrared telescope and explain what the evidence supports.',48,262,1136,82,29);
  block(s,'The problem', 'Two images of the same sky can look different because a star moved, the telescope sampled another infrared wavelength, or a pixel is unreliable. Seeing a change is only the start; the observer needs a way to decide what caused it.',48,381,553,176,23);
  block(s,'What we built','Perigee combines aligned images, guided comparison checks and a saved evidence notebook. A learner finishes with their own explanation, the observations behind it and links back to NASA’s archive. Three cases teach the process; five targets and live search extend it.',671,381,561,176,23);
  text(s,'Team Perigee · Planet X and SPHEREx challenge',48,607,1184,28,21,C.accent,true);
  text(s,'Sathvik Loke · Sagar Raut · Akshobya Rao · Aditya Raut · Suhrit Bestavemula · Neeraj Movva',48,645,1184,25,18,C.muted);
 }
 if(i===1){
  base(s,i,'PRODUCT WALKTHROUGH','From a first look to a supported explanation');
  img(s,root+'/docs/presentation/standalone-assets/barnard-app.png',48,158,510,475,'Current Perigee app: Barnard’s Star A+C comparison, Play comparison button, dates, wavelengths, quality labels and predicted positions');
  block(s,'1  Choose and play','Open a guided case and press Play comparison. The two images alternate in the same position, making small changes easier to spot against nearby stars.',603,155,629,92,23);
  block(s,'2  Check the comparison','Barnard’s Star is shown on 25 Aug 2025 and 19 Aug 2026 at nearly the same infrared wavelength. Its glow shifts north against the field stars, consistent with the catalog prediction of about seven display pixels (10 arcseconds).',603,306,629,115,23);
  block(s,'3  Explain and keep the evidence','The learner records what they noticed, what it supports and what is uncertain. After the checks and notes are complete, a reference answer helps them reflect. Their own words remain saved and can be reopened, printed or exported.',603,479,629,129,23);
  source(s,'Actual app screenshot · NASA/IPAC SPHEREx images · The ring is a catalog prediction; the saturated center limits precise position measurements.');
 }
 if(i===2){
  base(s,i,'THREE GUIDED INVESTIGATIONS','Each case teaches a different comparison');
  text(s,'Wavelength is the “color” of infrared light, measured here in micrometers (µm). Problem flags mark pixels the mission pipeline considers unreliable.',48,145,1184,67,23,C.muted);
  const rows=[
   {y:235,n:'Barnard’s Star',q:'Can you see a star move?',a:paths.ba,b:paths.bc,cap:'25 Aug 2025 / 19 Aug 2026',body:'Across a year near 2.0 µm, the glow shifts north while field stars stay nearly fixed. This agrees with the predicted motion. The bright core overloads the detector, limiting its exact image position.'},
   {y:376,n:'Epsilon Indi B',q:'Is this a fair comparison?',a:paths.ea,b:paths.ec,cap:'Same exposure · 29 Apr 2026',body:'One pair compares dates five months apart near 2.323 µm. Another compares 2.3232 and 4.9399 µm at the same moment. The latter tests wavelength, not time. The learner also checks display contrast before interpreting a difference in gray level.'},
   {y:517,n:'WISE 0855 field',q:'A dot that jumps',a:paths.wa,b:paths.wb,cap:'7 Nov 2025 / 10 Nov 2025',body:'A bright dot appears to jump over three days at closely matched wavelength. The quality overlay identifies the unreliable feature. The learner can explain why this apparent jump is insufficient evidence for a moving celestial object.'}];
  for(const r of rows){img(s,r.a,48,r.y,96,96,r.n+' first SPHEREx image');img(s,r.b,154,r.y,96,96,r.n+' second SPHEREx image');text(s,r.cap,48,r.y+104,230,31,13,C.muted);text(s,r.n+' · '+r.q,287,r.y,945,36,26,C.accent,true);text(s,r.body,287,r.y+43,945,94,22.5);}
 }
 if(i===3){
  base(s,i,'NASA DATA & IMPLEMENTATION','How archive files become a usable investigation');
  const columns=[
   {x:48,w:350,h:'1  Retrieve the data',t:'NASA/IPAC’s Infrared Science Archive (IRSA) provides SPHEREx Level 2 observations from Data Release 1 and Quick Release 3. We retrieve small FITS cutouts: scientific files containing pixels, observation times, wavelength information and quality flags.',t2:'Object names resolve through SIMBAD/Sesame. Search also accepts decimal or sexagesimal sky coordinates, such as hours:minutes:seconds.'},
   {x:455,w:350,h:'2  Process consistently',t:'Python uses each file’s sky coordinates to place observations on one fixed, north-up grid. It reads the wavelength at the target’s detector position, converts pixel values into a stated display contrast, and preserves quality information.',t2:'Display contrast maps measurements to gray; different scales can make the same value look different. The target marker is a catalog prediction.'},
   {x:862,w:370,h:'3  Deliver in the browser',t:'React and TypeScript provide comparison playback, optional flag overlays, guided checks and the notebook. Cloudflare serves the app and prepared cases; a Python/FastAPI service on Vercel handles live archive requests.',t2:'Two frame requests run at once, with bounded retries and a cache of completed results. The first ready image is usable while others load.'}];
  for(const a of columns){text(s,a.h,a.x,159,a.w,43,27,C.accent,true);text(s,a.t,a.x,218,a.w,246,23);line(s,a.x,477,a.w);text(s,a.t2,a.x,498,a.w,138,22);}
  source(s,'NASA/IPAC IRSA: irsa.ipac.caltech.edu/Missions/spherex.html · SIMBAD: target context · ESA Gaia DR3: independent field-star checks');
 }
 if(i===4){
  base(s,i,'PROCESSING & SCIENTIFIC VALIDATION','Checks that make the comparisons inspectable');
  text(s,'We checked the processed images against their source files and tested alignment against an external star catalog. The checks answer different questions.',48,145,1184,68,24,C.muted);
  text(s,'189 image records',48,247,552,55,43,C.accent,true);text(s,'SOURCE-FILE CONSISTENCY',48,310,552,28,18,C.accent,true);
  text(s,'The 14–15 November processing sweep covered 183 unique cutouts plus six case re-renders. A separate code path recomputed wavelengths, timestamps, quality flags, coverage, display mapping and source records. The results matched the published products, so the displayed evidence can be traced back to the original files.',48,356,552,224,23);
  text(s,'128 PASS · 55 UNKNOWN · 0 FAIL',670,252,562,92,32,C.accent,true);text(s,'183 UNIQUE CUTOUTS · EXTERNAL ALIGNMENT',670,344,562,27,17,C.accent,true);
  text(s,'Independent field-star detections were compared with Gaia DR3 positions. PASS means the alignment met the validator’s thresholds; UNKNOWN means too few usable stars supported a verdict. Unknown cases stay visible as uncertainty. This check tests the sky grid separately from the moving target.',670,391,562,194,23);
  line(s,48,588,1184);text(s,'Deliberate error test',48,607,295,32,24,C.text,true);text(s,'The validator rejected every injected 1-, 2- and 5-native-pixel shift on the three tested real-frame fixtures.',363,605,869,57,22.5);
 }
 if(i===5){
  base(s,i,'OUR CONTRIBUTION','A saved explanation with the data behind it');
  block(s,'One continuous investigation','Perigee connects image comparison, scientific checks and learner-written reasoning in one workflow. The learner chooses an interpretation and explains it using the selected observations. The reference appears after they record their own thinking.',48,159,553,155,23);
  block(s,'Someone else can inspect the reasoning','Each export retains the observation IDs, dates, wavelengths, quality results, archive URLs, raw-file SHA-256 fingerprints and processing details. The notes autosave in the browser. JSON preserves the structured record; printing creates a PDF for a teacher, classmate or club.',48,404,553,187,23);
  text(s,'EXAMPLE COMPLETED EVIDENCE CARD',671,164,561,28,18,C.accent,true);
  text(s,'Observation',671,215,561,32,24,C.text,true);text(s,'In images A and C, the bright glow shifts north relative to the surrounding stars.',671,254,561,70,23,C.muted);
  text(s,'Explanation',671,350,561,32,24,C.text,true);text(s,'The shift is consistent with Barnard’s Star moving across the sky, as the catalog predicts.',671,390,561,70,23,C.muted);
  text(s,'Evidence and uncertainty',671,485,561,32,24,C.text,true);text(s,'A: 25 Aug 2025, 2.0062 µm. C: 19 Aug 2026, 2.0284 µm. The core is saturated, so its exact center is uncertain. The exported card links both observations to IRSA.',671,526,561,112,23,C.muted);
  source(s,'Illustrative completed record, not a user testimonial. The contribution is the integrated reasoning workflow and retained provenance.');
 }
 if(i===6){
  base(s,i,'PEOPLE, REUSE & PROJECT LINKS','Why this is useful beyond a single demonstration');
  block(s,'For a student','Start with a concrete question and real NASA images. Practice separating what is visible from the explanation it supports. Leave with a written conclusion that can be discussed, rather than only a screenshot.',48,158,620,115,23);
  block(s,'For a teacher or astronomy club','Use a guided case as a short activity. Compare explanations against the same observations, then discuss how dates, wavelengths or unreliable pixels shaped the conclusion. No account or installation is needed.',48,336,620,127,23);
  block(s,'A reason to return','Reopen saved notes or try another target: Barnard’s Star, Epsilon Indi B, WISE 0855, RW Aurigae or R Draconis. Live search extends the workflow to your own object or coordinates.',48,511,620,110,22.5);
  text(s,'OPEN THE PROJECT',747,161,485,30,19,C.accent,true);
  link(s,'perigee.lokesathvik.workers.dev','https://perigee.lokesathvik.workers.dev/',747,210,485,70,27);
  text(s,'Start with Barnard’s Star. Play the comparison, follow the checks, then save an evidence card.',747,298,485,100,24);
  text(s,'READ THE METHODS & CODE',747,439,485,30,19,C.accent,true);
  link(s,'github.com/sathvikloke/perigee','https://github.com/sathvikloke/perigee',747,481,485,57,23);
  link(s,'Technical report (8 pages)','https://perigee.lokesathvik.workers.dev/demo/perigee-technical-report.pdf',747,554,485,35,23);
  text(s,'Processing, experiments, source links and reproduction instructions are public.',747,600,485,54,20,C.muted);
 }
 }
 return {updated:input.slides,slides:presentation.slides.items.length};
}
