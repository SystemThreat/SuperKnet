import {layout} from './worker.js';import fs from 'fs';
const ref=JSON.parse(fs.readFileSync('./sample_layout.json'));
const t=Date.now(),l=layout(ref.address);console.log('ms',Date.now()-t,'seed ok',l.seed_hex===ref.seed_hex);
const ok=ref.pieces.every((p,i)=>p.family===l.pieces[i].family&&p.cells.join()===l.pieces[i].cells.join());console.log('pieces match',ok);
