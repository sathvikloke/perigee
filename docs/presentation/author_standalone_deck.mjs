// Live Artifact Session callback. Execute with its prebound presentation, never as a standalone deck builder.
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const C={bg:'#080A0A',text:'#F5F6F5',muted:'#AFB6BA',accent:'#D7FC70',line:'#343B3B',panel:'#141919'};
function text(s,t,x,y,w,h,size=23,color=C.text,bold=false){const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=t;a.text.style={fontSize:size,typeface:'Avenir Next',color,bold,autoFit:'none',wrap:'square',insets:0};return a;}
function line(s,x,y,w,color=C.line){s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:1},fill:color,line:{fill:'none',width:0}});}
function img(s,path,x,y,w,h,alt){s.images.add({path,alt,position:{left:x,top:y,width:w,height:h},fit:'contain'});}
function link(s,label,url,x,y,w,h,size=20,color=C.accent){const a=text(s,label,x,y,w,h,size,color);a.text.get(label).link={uri:url,isExternal:true};}
function base(s,i,k,title){s.background.fill=C.bg;text(s,`PERIGEE   /   ${k}`,48,26,1140,26,17,C.accent,true);text(s,title,48,65,1184,66,42,C.text,true);line(s,48,678,1184);text(s,'NASA Space Apps 2026. Planet X and SPHEREx.',48,691,1010,19,14,C.muted);text(s,`${i+1} / 7`,1168,689,70,23,16,C.muted);}
function source(s,t){text(s,t,48,649,1184,24,14,C.muted);}
function block(s,head,body,x,y,w,bodyH,size=23){text(s,head,x,y,w,37,26,C.accent,true);text(s,body,x,y+45,w,bodyH,size);}
const paths={ba:root+'/backend/content/presets/barnards_star/case-moving_neighbor/2025W35_1A_0008_1_D3.png',bc:root+'/backend/content/presets/barnards_star/case-moving_neighbor/2026W34_1A_0431_1_D3.png',ea:root+'/backend/content/presets/epsilon_indi_b/case-fair_comparison/2026W18_1A_0516_1_D3.png',ec:root+'/backend/content/presets/epsilon_indi_b/case-fair_comparison/2026W18_1A_0516_1_D6.png',wa:root+'/backend/content/presets/wise_0855/case-wise_0855_quality_trap/2025W45_2A_0278_1_D2.png',wb:root+'/backend/content/presets/wise_0855/case-wise_0855_quality_trap/2025W46_1A_0108_1_D2.png'};
const notes=[
`Sources: https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/ ; docs/TEAM.md ; docs/SUBMISSION_DRAFT.md. Perigee supplies public name/coordinate search and time-ordered images, with guided investigations as the educational contribution. The student example is a proposed use, not a testimonial or measured outcome. All six authors are listed.`,
`Sources: backend/content/cases/moving_neighbor.json ; science/reviews/overnight-controls/README.md section D ; frontend/src/components/CaseBench.tsx ; frontend/src/components/Notebook.tsx. The app screenshot was captured 15 November 2026. Case A/C dates are 25 August 2025 and 19 August 2026; wavelengths are 2.0062 and 2.0284 micrometers. Catalog displacement is 7.29 display pixels or 10.25 arcseconds. All 11 retained visual proxies point north, with A/C shifts 6.87–8.87 display pixels. Saturation prevents precision astrometry.`,
`Sources: backend/content/cases/moving_neighbor.json, fair_comparison.json and wise_0855_quality_trap.json ; science/reviews/overnight-controls/README.md sections B–D. Images are original processed NASA/IPAC SPHEREx observations. Epsilon A/C share an exposure but differ in wavelength, detector and display scale. WISE P/Q span 2.655 days, and the feature is not identified as WISE 0855. The source data and controls support the stated decisions, not a new astronomical discovery.`,
`Sources: science/reviews/targets/README.md ; backend/content/presets ; backend/data/process.py ; backend/data/archive.py ; https://irsa.ipac.caltech.edu/Missions/spherex.html ; https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/ ; https://simbad.cfa.harvard.edu/simbad/ ; https://www.cosmos.esa.int/web/gaia/dr3. The target review checks identities, catalog positions/epochs, propagated markers and shipped records for all five challenge targets. RW Aurigae is unresolved A+B at SPHEREx resolution. R Draconis is saturated in the reviewed sample; neither target supplies a measured variability claim. Shared sky grid defaults to 256 pixels over 6 arcminutes with north up and east left.`,
`Sources: science/reviews/overnight-controls/README.md section B and retained results ; science/reviews/acceptance/README.md ; science/reviews/registration-audit/README.md. WISE F1 occupies detector coordinate (1709,1364), not a shared cutout-native coordinate: the raw cutout pixels are (29,40) and (30,40). WCS sky separation is 5.36 arcseconds; field-star-implied prediction for a detector-fixed feature is 5.38 arcseconds. Three strict field sources have median sky shift 0.40 and maximum 0.76 arcseconds. Flags include TRANSIENT, SUR_ERROR and NONFUNC. Physical cause is unestablished. Historical 189 processing records comprise 183 unique cutouts plus six re-renders. Alignment verdicts for the unique set are 128 PASS, 55 UNKNOWN, 0 FAIL. UNKNOWN is fewer than three usable supporting stars. Nine deliberate shifts cover 1/2/5 native pixels on three real-frame fixtures; this is a retained test, not a population benchmark.`,
`Sources: two excerpts of an actual completed evidence-card preview captured from Perigee for this deck ; frontend/src/components/Notebook.tsx ; science/reviews/contribution/README.md. The displayed example is an authored demonstration, not a participant record. Existing astronomy viewers and education projects already provide comparison, quality information and cases. The contribution is the connection to learner-authored reasoning and an exact portable source record. Notes save locally in the browser. JSON retains structured provenance, while print/Save as PDF produces a readable record.`,
`Sources: docs/SUBMISSION_DRAFT.md ; docs/AI_USE.md ; docs/report/TECHNICAL_REPORT.md. Teaching and club scenarios describe intended use. The technical report is 10 pages. All linked artifacts must be verified publicly accessible before submission. Claude Code and OpenAI Codex assisted implementation and materials. The app uses deterministic scientific processing. The deck uses scientific observations and app/export screenshots, not generated scientific imagery.`];
export async function build({presentation,input}){
 for(const i of input.slides){const old=await presentation.inspect({select:`$.slides[${i}].elements[*]`,include:['id']});if(old.records.length)presentation.delete(old.records.map(x=>x.id));const s=presentation.slides.getItem(i);s.speakerNotes.text=notes[i];
 if(i===0){
  base(s,i,'PROJECT & PURPOSE','');text(s,'Perigee',48,71,710,100,84,C.text,true);text(s,'An investigation of NASA’s infrared sky',48,181,1184,60,40,C.accent,true);
  text(s,'Enter an object name or sky position. Explore a sequence of SPHEREx observations, then explain what the images support.',48,263,1136,92,31);
  block(s,'The learner’s question','A student sees a star shift between two images. Is it motion, a different infrared wavelength, or an unreliable pixel? Dates and quality information help the student test that first impression.',48,387,553,156,23);
  block(s,'Our contribution','A public time-sequence viewer, three guided investigations and a portable evidence notebook. The learner’s explanation stays attached to the observations and exact archive sources that support it.',671,387,561,156,23);
  text(s,'Team Perigee. Planet X and SPHEREx challenge.',48,607,1184,28,21,C.accent,true);
  text(s,'Sathvik Loke, Sagar Raut, Akshobya Rao, Aditya Raut, Suhrit Bestavemula and Neeraj Movva',48,645,1184,25,18,C.muted);
 }
 if(i===1){
  base(s,i,'THE LEARNER EXPERIENCE','A student follows the evidence');
  img(s,root+'/docs/presentation/standalone-assets/barnard-app.png',48,158,510,475,'Perigee Barnard’s Star comparison with real NASA images, dates, wavelengths, quality information and playback');
  block(s,'1  Notice the shift','Play Barnard’s Star’s comparison. Its bright glow shifts north against surrounding stars between August 2025 and August 2026.',603,159,629,91,24);
  block(s,'2  Check the explanation','The pair uses nearly the same wavelength. The shift agrees in direction and approximate size with the catalog prediction. The saturated core limits precise position measurements.',603,310,629,118,24);
  block(s,'3  Keep a reasoned conclusion','The student records what changed, what it supports and what remains uncertain. A reference helps them reflect. The saved evidence lets a teacher revisit the observations behind the answer.',603,490,629,126,24);
  source(s,'Actual app screenshot. NASA/IPAC SPHEREx observations. The target ring marks a catalog prediction.');
 }
 if(i===2){
  base(s,i,'THREE GUIDED INVESTIGATIONS','Three decisions a learner can explain');
  text(s,'Each case makes a different question concrete. Wavelength is the “color” of infrared light. Quality flags identify pixels that need care.',48,145,1184,67,23,C.muted);
  const rows=[
   {y:235,n:'Barnard’s Star',q:'Recognize apparent motion',a:paths.ba,b:paths.bc,cap:'25 Aug 2025 / 19 Aug 2026',body:'At similar wavelengths near 2.0 µm, the glow shifts north while neighboring stars remain nearly fixed. The learner can support a qualitative motion interpretation and explain why saturation limits a precise measurement.'},
   {y:376,n:'Epsilon Indi B',q:'Choose a fair comparison',a:paths.ea,b:paths.ec,cap:'Same exposure, 29 Apr 2026',body:'A five-month pair explores time at similar wavelengths. The pictured pair shows 2.3232 and 4.9399 µm at the same moment. The learner separates wavelength from time and checks display contrast before comparing gray levels.'},
   {y:517,n:'WISE 0855 field',q:'Test an apparent jump',a:paths.wa,b:paths.wb,cap:'7 Nov 2025 / 10 Nov 2025',body:'A flagged bright dot appears to move over three days. A detector-coordinate control explains its sky shift as the pointing changes. The learner can reject a moving-object claim using the flags and a testable alternative.'}];
  for(const r of rows){img(s,r.a,48,r.y,96,96,r.n+' first SPHEREx image');img(s,r.b,154,r.y,96,96,r.n+' second SPHEREx image');text(s,r.cap,48,r.y+104,230,31,13,C.muted);text(s,r.n+': '+r.q,287,r.y,945,36,26,C.accent,true);text(s,r.body,287,r.y+43,945,94,22.5);}
 }
 if(i===3){
  base(s,i,'CHALLENGE IMPLEMENTATION','Public search. Five reviewed target fields.');
  block(s,'An object name or a sky position','Name resolution or decimal/sexagesimal coordinates locate a field. NASA/IPAC IRSA supplies SPHEREx Level 2 FITS observations from Data Release 1 and Quick Release 3.',48,157,531,144,23);
  block(s,'A sequence with context','Python places images on a fixed north-up sky grid and retains dates, wavelengths, quality flags and source links. The browser can play the sequence while completed frames remain cached.',48,379,531,152,23);
  text(s,'React/TypeScript frontend on Cloudflare. Python/FastAPI service with Astropy, NumPy and Pillow.',48,592,531,52,19,C.muted);
  text(s,'RETAINED TARGET REVIEW',643,162,589,30,18,C.accent,true);
  const targets=[
   ['Barnard’s Star','Apparent northward shift. Saturation limits precision.'],
   ['Epsilon Indi B','Time and wavelength comparisons, with display context.'],
   ['WISE 0855 field','A detector-fixed feature tests a moving-object interpretation.'],
   ['RW Aurigae','An unresolved binary calls for system-level interpretation.'],
   ['R Draconis','Saturation must be checked before comparing brightness.']];
  targets.forEach(([name,body],j)=>{const y=209+j*86;text(s,name,643,y,589,29,23,C.text,true);text(s,body,643,y+34,589,47,21,C.muted);});
  source(s,'All five: catalog identity, position/epoch, propagated marker and shipped records reviewed. RW Aurigae and R Draconis have no variability claim.');
 }
 if(i===4){
  base(s,i,'RETAINED SCIENTIFIC CHECKS','A convincing jump has a testable explanation');
  text(s,'5.36″ observed. 5.38″ predicted.',48,161,1184,58,42,C.accent,true);
  text(s,'The shifts above are in arcseconds. The feature stays at detector pixel (1709, 1364). Three usable stars predict almost the same apparent sky shift for that fixed pixel as the pointing changes. Their own sky positions agree within 0.76″.',48,242,1184,97,26);
  text(s,'Adverse mission flags support the check. The feature’s physical cause remains unknown.',48,355,1184,41,23,C.muted);
  line(s,48,418,1184);
  block(s,'183 unique cutouts. 189 records.','The historical processing audit includes six case re-renders. A separate code path reproduced source-file values, display mapping and provenance from the FITS inputs.',48,448,553,112,22.5);
  block(s,'128 PASS. 55 UNKNOWN. 0 FAIL.','Independent Gaia field-star alignment checks cover the 183 unique cutouts. UNKNOWN means too few usable stars. Alignment verdicts do not certify source identity.',671,448,561,112,22.5);
  source(s,'Control test: all nine deliberate 1-, 2- and 5-native-pixel shifts on three real-frame fixtures were rejected. Methods and inputs are retained.');
 }
 if(i===5){
  base(s,i,'OUR CONTRIBUTION','The explanation travels with its evidence');
  block(s,'A learner-authored result','The student writes an observation, an explanation and remaining uncertainty. A completed investigation produces a record someone else can inspect and question.',48,164,553,119,24);
  block(s,'The exact observations remain attached','The export retains frame IDs, dates, wavelengths, quality results, display settings and archive URLs. File fingerprints and processing details trace the images to their inputs.',48,355,553,145,24);
  text(s,'Existing viewers already compare images. Perigee connects that activity to a short investigation and a portable record of the learner’s reasoning.',48,563,553,77,21,C.muted);
  text(s,'COMPLETED EVIDENCE CARD',671,151,561,26,17,C.accent,true);
  img(s,root+'/docs/presentation/standalone-assets/evidence-export.jpg',671,180,561,315,'Actual completed Perigee evidence-card preview excerpt showing the authored demonstration notes');
  img(s,root+'/docs/presentation/standalone-assets/evidence-observations.jpg',671,515,561,110,'Actual evidence-card preview excerpt showing observation dates, wavelengths, quality results and archive links');
  source(s,'Excerpts of an actual evidence card authored for this demonstration. JSON preserves the structured record and its source references.');
 }
 if(i===6){
  base(s,i,'PEOPLE & PROJECT LINKS','A conclusion a class can discuss');
  block(s,'A student has something to explain','The activity starts with a visible change. The student tests an interpretation and leaves with their own conclusion, supported by named observations.',48,158,620,114,24);
  block(s,'A teacher can inspect the reasoning','Give a class the same image pair, then compare their explanations. Each saved record shows which dates, wavelengths and quality evidence shaped the answer.',48,338,620,123,24);
  block(s,'A new question gives a reason to return','Try another investigation, reopen saved work or search a new object. Astronomy clubs can debate the WISE feature and inspect the retained control together.',48,516,620,111,23);
  text(s,'OPEN THE PROJECT',747,161,485,30,19,C.accent,true);
  link(s,'perigee.lokesathvik.workers.dev','https://perigee.lokesathvik.workers.dev/',747,210,485,70,27);
  text(s,'Start with Barnard’s Star. Play the comparison, follow the checks and save an evidence record.',747,298,485,100,24);
  text(s,'READ THE METHODS & CODE',747,439,485,30,19,C.accent,true);
  link(s,'github.com/sathvikloke/perigee','https://github.com/sathvikloke/perigee',747,481,485,57,23);
  link(s,'Technical report (10 pages)','https://perigee.lokesathvik.workers.dev/demo/perigee-technical-report.pdf',747,554,485,35,23);
  text(s,'Processing, control experiments and source records are public.',747,600,485,54,20,C.muted);
 }
 }
 return {updated:input.slides,slides:presentation.slides.items.length};
}
