import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, ExternalLink, Search } from '../ui/Icons'

// Everything the project builds on. Facts are copied from
// docs/models/MODEL_CARD.md, docs/research/DATASETS.md,
// docs/research/EVALUATION.md, backend/requirements*.txt and README.md.
//
// Entry fields: title, detail (one line), note (licence / where it lives),
// url (optional), used (code paths), facts (key details), status (optional).

const HF = (id) => `https://huggingface.co/${id}`
const DOI = (d) => `https://doi.org/${d}`

export const REFERENCES = [
  {
    group: 'Models', color: 'var(--acid)',
    items: [
      { title: 'haywoodsloan/ai-image-detector-deploy', detail: 'SwinV2 scene detector for AI-generated images', note: 'Hugging Face',
        url: HF('haywoodsloan/ai-image-detector-deploy'), status: 'In the image verdict',
        used: ['backend/app/ml/image_pipeline.py'],
        facts: ['Weight 0.75 in the scene ensemble', 'P(AI) = 1 − P(its "real" class)', 'Replaced umm-maybe/AI-image-detector on 2026-10-05'] },
      { title: 'OwensLab/commfor-model-384', detail: 'Community Forensics ViT-S/384 scene detector', note: 'Hugging Face',
        url: HF('OwensLab/commfor-model-384'), status: 'In the image verdict',
        used: ['backend/app/ml/commfor.py', 'timm (model definition)'],
        facts: ['Weight 4, chosen on the dev half of COCO val2017 + Synthbuster', 'Evidence: evaluation/COMMFOR-02/scene_detector_eval_dev.json'] },
      { title: 'Community Forensics, fine-tuned here (v3)', detail: 'The same ViT fine-tuned on FLUX.2, GPT Image 2 and Nano Banana 2', note: 'checkpoints/commfor_ft_v3/',
        status: 'In the image verdict',
        used: ['ml/training/finetune_commfor.py', 'ml/training/calibrate_commfor.py'],
        facts: ['Weight 4, equal to the original (fixed before the test sets were scored)', 'Calibrated so ≤ 1 % of validation real images score ≥ 0.5', 'Alone it called 6.4 % of COCO test photos AI (evaluation/COMMFOR-FT-01/old_v3.json)', 'A later v4 was tested and rejected (evaluation/COMMFOR-FT-02)'] },
      { title: 'TruFor (Guillaro et al., CVPR 2023)', detail: 'Integrity score and heatmap of possibly edited regions', note: 'GRIP-UNINA licence, nonprofit use only',
        status: 'Shown, not in the verdict',
        used: ['backend/app/ml/trufor.py', 'backend/app/ml/trufor_vendor/'],
        facts: ['A region is reported at score ≥ 0.8, flagging ≤ 2 % of real COCO dev photos', 'Kept out of the verdict: flags 10 % of re-compressed social-media photos and does not detect fully generated images', 'Evidence: evaluation/TRUFOR-01/results.json'] },
      { title: 'Sadanie/pellav2-audio-deepfake-detector', detail: 'pellav2: w2v-BERT 2.0 encoder, weighted sum of all hidden layers, linear head', note: 'MIT',
        url: HF('Sadanie/pellav2-audio-deepfake-detector'), status: 'Audio verdict',
        used: ['backend/app/ml/audio/pellav2.py (copied from the authors’ pellav2_infer.py)'],
        facts: ['580.5 M parameters; training data not published by its authors', 'Revision 29daea8b04acf2d3f11d1d0da6b01c17fc8a1e4b', 'Weights sha256 d21aedfb52e2f87706c2753715a29665482b0f4a034800c31579df5d458559ac', 'Up to 8 windows of 4 s, each at −23 LUFS; AI at ≥ 0.58, authentic below 0.42'] },
      { title: 'facebook/w2v-bert-2.0', detail: 'Encoder configuration pellav2 is built on', note: 'Hugging Face',
        url: HF('facebook/w2v-bert-2.0'), used: ['backend/app/ml/audio/pellav2.py'], facts: ['80-bin Kaldi filterbank input at 16 kHz mono'] },
      { title: 'LCNN on LFCC, trained here', detail: 'Light CNN anti-spoofing model, 144,065 parameters', note: 'checkpoints/audio_lcnn_asvspoof_lfcc_seed2.pt',
        status: 'Audio fallback',
        used: ['backend/app/ml/audio/lcnn_asvspoof.py', 'ml/training/train_asvspoof.py', 'paper/config/audio_calibration.json'],
        facts: ['LFCC: 20 coefficients + deltas + double deltas, 4 s windows', 'Class-balanced Platt scaling fitted on dev', 'LA eval: EER 4.78 %, min t-DCF 0.102, AUC 0.986 (results/audio_eval.json)', 'The backend refuses any checkpoint whose sha256 differs from the calibration file'] },
      { title: 'yermandy/GenD_CLIP_L_14', detail: 'GenD (Yermakov et al., WACV 2026): CLIP ViT-L/14 with a layer-norm-tuned linear head', note: 'MIT',
        url: HF('yermandy/GenD_CLIP_L_14'), status: 'Video face-swap verdict',
        used: ['backend/app/ml/gend.py', 'backend/app/ml/video/gend_model.py'],
        facts: ['Pretrained by its authors on FaceForensics++; not trained here', 'Face crop: MTCNN box enlarged 1.3× and squared', 'Face score = mean P(fake) over sampled face frames', 'Face AUC 0.941 on 400 DFD videos (evaluation/VIDEO-GEND-01/results.json)'] },
      { title: 'MTCNN (facenet-pytorch)', detail: 'Face detection and cropping for images and video', note: 'backend/requirements-ml.txt',
        used: ['backend/app/ml/faces.py'], facts: ['Shared by the image face model and GenD'] },
      { title: 'EfficientNet-B4 face-crop classifier', detail: 'Trained here on 140k Real and Fake Faces (FFHQ vs StyleGAN)', note: 'checkpoints/image_detector.pt',
        status: 'Switched off',
        used: ['FACE_MODEL_IN_VERDICT=false'],
        facts: ['Its 99.98 % validation accuracy measured memorisation: 144,000 of 164,000 validation images were copies of training faces', 'On real photos it flagged 21 % of real faces and 15 % of AI faces', 'On 400 DFD videos its face AUC was 0.533'] },
      { title: 'Organika/sdxl-detector', detail: 'Former scene detector', note: 'Hugging Face', url: HF('Organika/sdxl-detector'), status: 'Removed',
        facts: ['AUC 0.596 on the newer-generator validation split; flagged 15.6 % of real images', 'Fusion unchanged without it (evaluation/COMMFOR-FT-01/val_ft1.json)'] },
      { title: 'umm-maybe/AI-image-detector', detail: 'The original primary image model', note: 'Hugging Face', url: HF('umm-maybe/AI-image-detector'), status: 'Removed',
        facts: ['AUC 0.469 on current generators: below chance', 'Replaced on 2026-10-05 (KNOWN_ISSUES.md, resolved)'] },
    ],
  },
  {
    group: 'Datasets', color: 'var(--teal)',
    items: [
      { title: 'ASVspoof 2019, logical access', detail: 'Training, every choice, and the audio test', note: 'ODC-By 1.0 · DOI 10.7488/ds/2555',
        url: DOI('10.7488/ds/2555'), used: ['ml/preprocessing/build_asvspoof2019_la.py'],
        facts: ['Official protocol files only: train to learn, dev for every choice, eval scored once', 'Train: 25,380 utterances, attacks A01–A06', 'Eval: 7,355 bona fide + 63,882 spoofed (71,237), attacks A07–A19 never seen in training'] },
      { title: 'ASVspoof 5 (evaluation sample)', detail: 'Held-out audio test, never used for any choice', note: 'ODC-By 1.0 · DOI 10.5281/zenodo.14498691',
        url: DOI('10.5281/zenodo.14498691'), used: ['evaluation/AUDIO-PELLAV2-01-ASVSPOOF5/'],
        facts: ['3,004 clips streamed from flac_E_aa.tar', '125 bona fide per codec condition (none, C01–C11) and 94 spoofed per attack (A17–A32)', 'Every kept clip decoded at 16 kHz with no failures'] },
      { title: 'COCO val2017', detail: 'Real photos for the image test', note: 'Flickr licences; annotations CC BY 4.0',
        url: 'https://cocodataset.org', used: ['evaluation/E2E-01/image_manifest.csv'],
        facts: ['600 photos, split 50/50 by image id into dev and test halves', 'Dev half: Community Forensics weight, the 0.02 cut-off, TruFor threshold', 'Test half: reporting only'] },
      { title: 'Synthbuster (Bammey 2023)', detail: 'AI images from nine generators', note: 'CC BY-NC-SA 4.0 · DOI 10.5281/zenodo.10066460',
        url: DOI('10.5281/zenodo.10066460'), used: ['evaluation/E2E-01/image_manifest.csv'],
        facts: ['200 images per generator (seed 0): DALL·E 2 and 3, Firefly, GLIDE, Midjourney v5, SD 1.3, 1.4, 2, SDXL', 'Same 50/50 dev / test split as COCO', 'No image is redistributed in the repository'] },
      { title: 'MLLM-Generated Image Detection Dataset (Zhang et al. 2026)', detail: 'Newest generators: fine-tuning and testing · arXiv 2608.01258', note: 'Apache-2.0 metadata; research use only',
        url: HF('datasets/zr-zhang/MLLM-Generated-Image-Detection-Dataset'), used: ['evaluation/COMMFOR-FT-01/', 'evaluation/E2E-02/'],
        facts: ['Test set: 653 real / 1,481 AI images (FLUX.2, GPT Image 2, Nano Banana 2, Qwen Image 2.1)', 'Shortcut control: its AI images are PNG and real ones mostly JPEG, so every image is re-encoded as JPEG before scoring'] },
      { title: 'DeepFake Detection (DFD), Google / Jigsaw', detail: 'Video test: 200 real and 200 face-swapped clips of paid, consenting actors', note: 'FaceForensics++ terms of use',
        url: HF('datasets/angads24/deepfake-video'), used: ['evaluation/VIDEO-GEND-01/', 'scripts/eval_video_detector.py'],
        facts: ['Copy used: Hugging Face mirror angads24/deepfake-video (official forms unavailable)', '120 videos (seed 0) diagnosed the video rules; 80 others (seed 1) are the held-out verdict test', 'GenD did not train on DFD; evaluation only'] },
      { title: '140k Real and Fake Faces (Kaggle)', detail: 'FFHQ real faces vs StyleGAN fakes', note: 'Kaggle',
        used: ['scripts/expand_training_dataset.py', 'checkpoints/image_detector*.pt'],
        facts: ['Training data of the face-crop classifier (switched off)', 'Its reported validation set contained derived copies of training images', '20 test images are the image inputs of the latency benchmark'] },
      { title: 'TruFor splice test (made here)', detail: '600 spliced copies of the COCO photos', note: 'backend/scripts/eval_trufor.py',
        facts: ['A feathered region from another photo of the same split, JPEG q90, seed 0', 'A controlled test of local edits, not a public benchmark'] },
      { title: 'In-the-Wild (Müller et al., 2022)', detail: 'Planned cross-dataset audio test', note: 'not downloaded', status: 'Not run',
        facts: ['Licence conflict (Apache 2.0 vs CC BY-SA 4.0) unresolved', 'results/pipeline_eval.json records it as not run (KNOWN_ISSUES #13)'] },
    ],
  },
  {
    group: 'Evaluation runs', color: '#ffb020',
    items: [
      { title: 'E2E-01', detail: 'First full-pipeline verdict runs', note: 'evaluation/E2E-01/summary.json',
        facts: ['Image test half before the fix: 2.0 % real called MANIPULATED, 74.5 % AI caught', 'Audio with pellav2: ASVspoof 2019 LA (97.7 % fakes caught, 0.3 % real flagged) and ASVspoof 5 (77.0 %, 15.0 %)'] },
      { title: 'E2E-02', detail: 'Image verdicts with the final settings (commit 445c4ac)', note: 'evaluation/E2E-02/summary.json',
        facts: ['COCO + Synthbuster test half: 98.4 % AI caught, 0 real photos flagged', 'Newest generators: 44.0 % caught, 44.4 % inconclusive', '256 px thumbnails: 38.3 % caught'] },
      { title: 'E2E-03', detail: 'Codec-hardened pellav2 fine-tune', note: 'evaluation/E2E-03/summary.json', status: 'Rejected',
        facts: ['ASVspoof 5 false alarms 15.0 % → 4.0 %, but fakes caught 77.0 % → 54.0 %', 'Missed the rule fixed before testing, so the original pellav2 stays'] },
      { title: 'COMMFOR-01 / COMMFOR-02', detail: 'Community Forensics on the dev half', note: 'evaluation/COMMFOR-02/',
        facts: ['Chose the weight 4 for Community Forensics in the scene ensemble'] },
      { title: 'COMMFOR-FT-01', detail: 'Fine-tuned model v3: validation and comparisons', note: 'evaluation/COMMFOR-FT-01/',
        facts: ['Removed Organika/sdxl-detector (val_ft1.json)', 'Showed the fine-tune alone over-flags real photos (old_v3.json)'] },
      { title: 'COMMFOR-FT-02', detail: 'Fine-tuned model v4', note: 'evaluation/COMMFOR-FT-02/', status: 'Rejected',
        facts: ['84.2 % of newest-generator images caught, but 2.0 % of COCO photos flagged', 'Rule fixed in advance: switch only if no test set gets worse'] },
      { title: 'VIDEO-GEND-01', detail: 'GenD face model and whole-pipeline video verdicts on DFD', note: 'evaluation/VIDEO-GEND-01/',
        facts: ['Face AUC: GenD 0.941 vs StyleGAN checkpoint 0.533 (400 videos)', 'Held-out 80: real flagged 2.5 %, face swaps caught 72.5 %, verdict AUC 0.886', 'Median latency 20.7 s per video (GenD on, RTX 5070)'] },
      { title: 'TRUFOR-01', detail: 'TruFor threshold on COCO dev', note: 'evaluation/TRUFOR-01/results.json',
        facts: ['Region threshold 0.8: the lowest that flags ≤ 2 % of real COCO dev photos'] },
      { title: 'AUDIO-PELLAV2-01 (+ ASVSPOOF5)', detail: 'pellav2 compared with the LCNN', note: 'evaluation/AUDIO-PELLAV2-01*/',
        facts: ['pellav2 EER 1.6 % on an ASVspoof 2019 LA eval sample, 18.5 % on an ASVspoof 5 eval sample (MODEL_CARD.md)'] },
      { title: 'results/ and paper_results/', detail: 'Published numbers and the per-item scores behind them', note: 'scripts/regenerate_results.py --check',
        facts: ['audio_eval.json, robustness.json, latency.json, pipeline_eval.json, image_eval.json', 'Every file in results/ is rebuilt from paper_results/ and checked'] },
    ],
  },
  {
    group: 'Project documents', color: 'var(--mint-soft)',
    items: [
      { title: 'docs/models/MODEL_CARD.md', detail: 'Every model: source, input, output, thresholds, limits', note: 'repository' },
      { title: 'docs/research/EVALUATION.md', detail: 'Every measured number and the file it is copied from', note: 'repository' },
      { title: 'docs/research/DATASETS.md', detail: 'Role, split, source and licence of each dataset', note: 'repository' },
      { title: 'docs/paper_upgrade/DATA_STATEMENT.md', detail: 'Full licences, checksums and split policies', note: 'repository' },
      { title: 'docs/models/RETRAINING_IMAGE.md', detail: 'How to retrain the image fine-tune', note: 'repository' },
      { title: 'KNOWN_ISSUES.md', detail: 'Open limitations and every resolved issue, with dates', note: 'repository' },
      { title: 'docs/SECURITY.md', detail: 'Authentication, upload rules, report integrity', note: 'repository' },
      { title: 'docs/architecture/SYSTEM_ARCHITECTURE.md', detail: 'Layers, data flow and design decisions', note: 'repository' },
      { title: 'docs/setup/', detail: 'Installation, environment variables and Docker guides', note: 'repository' },
    ],
  },
  {
    group: 'Software', color: '#ececed',
    items: [
      { title: 'React 18 · Vite · Tailwind CSS · Framer Motion · Recharts', detail: 'Frontend', note: 'frontend/package.json' },
      { title: 'FastAPI · Pydantic · SQLAlchemy 2 · Alembic', detail: 'API and database layer', note: 'backend/requirements.txt' },
      { title: 'Celery · Redis · PostgreSQL', detail: 'Job queue and storage', note: 'docker-compose.yml' },
      { title: 'PyTorch · torchvision · Transformers · timm · safetensors', detail: 'Model inference', note: 'backend/requirements-ml.txt' },
      { title: 'OpenCV · facenet-pytorch · imagehash', detail: 'Image and video processing, face detection', note: 'backend/requirements-ml.txt' },
      { title: 'librosa · scipy · soundfile · imageio-ffmpeg', detail: 'Audio loading, signal processing, codecs', note: 'backend/requirements-ml.txt' },
      { title: 'ReportLab · Matplotlib', detail: 'PDF reports and their charts', note: 'backend/requirements.txt' },
      { title: 'Playwright · Vitest · pytest', detail: 'Browser, frontend and backend tests', note: 'package.json · requirements-dev.txt' },
      { title: 'Docker Compose', detail: 'Six-container deployment', note: 'docker-compose.yml' },
    ],
  },
]

const STATUS_COLOR = {
  'In the image verdict': 'var(--acid)', 'Audio verdict': 'var(--acid)', 'Video face-swap verdict': 'var(--acid)',
  'Audio fallback': 'var(--teal)', 'Shown, not in the verdict': 'var(--mint-soft)',
  'Switched off': '#ffb020', 'Not run': '#ffb020', Removed: '#ff4d3d', Rejected: '#ff4d3d',
}

function Entry({ item, index }) {
  const [open, setOpen] = useState(false)
  const expandable = Boolean(item.facts?.length || item.used?.length)
  return (
    <li className="border-b-2 border-[var(--border-subtle)] last:border-b-0" style={{ background: index % 2 ? 'var(--surface-1)' : 'var(--surface-2)' }}>
      <div className="grid gap-1 p-4 sm:grid-cols-[2.5rem_1.4fr_1fr_2rem] sm:items-center sm:gap-4">
        <span className="mono text-[0.75rem] font-bold text-ink-muted">[{String(index + 1).padStart(2, '0')}]</span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {item.url ? (
              <a href={item.url} target="_blank" rel="noreferrer" className="group inline-flex items-center gap-1.5 font-bold text-ink-primary hover:text-accent">
                <span className="break-words">{item.title}</span>
                <ExternalLink size={13} className="shrink-0 opacity-60 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </a>
            ) : (
              <span className="break-words font-bold text-ink-primary">{item.title}</span>
            )}
            {item.status && (
              <span className="mono rounded-sm border-2 border-[#191919] px-1.5 py-0.5 text-[0.5625rem] font-bold uppercase text-[#191919]"
                    style={{ background: STATUS_COLOR[item.status] || '#ececed' }}>{item.status}</span>
            )}
          </div>
          <p className="mt-0.5 text-[0.875rem] text-ink-secondary">{item.detail}</p>
        </div>
        <span className="mono text-[0.6875rem] text-ink-muted sm:text-right">{item.note}</span>
        {expandable ? (
          <button onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-label={`${open ? 'Hide' : 'Show'} details for ${item.title}`}
                  className="grid h-8 w-8 place-items-center justify-self-start rounded-md border-2 transition-all sm:justify-self-end"
                  style={{ borderColor: open ? '#191919' : 'var(--border-strong)', background: open ? 'var(--acid)' : 'transparent', color: open ? '#191919' : undefined }}>
            <ChevronDown size={16} className={`transition-transform duration-300 ${open ? 'rotate-180' : ''}`} />
          </button>
        ) : <span />}
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }} className="overflow-hidden">
            <div className="grid gap-4 px-4 pb-5 sm:ml-[3.5rem] sm:grid-cols-[1.4fr_1fr]">
              {item.facts?.length > 0 && (
                <div>
                  <p className="mono text-[0.6875rem] font-bold uppercase text-accent">Key facts</p>
                  <ul className="mt-2 space-y-1.5">
                    {item.facts.map((f) => (
                      <li key={f} className="flex gap-2 text-[0.875rem] text-ink-primary">
                        <span className="mt-2 h-1.5 w-1.5 shrink-0" style={{ background: 'var(--acid)' }} />
                        <span className="break-words">{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {item.used?.length > 0 && (
                <div>
                  <p className="mono text-[0.6875rem] font-bold uppercase text-accent">Used in</p>
                  <ul className="mt-2 space-y-1.5">
                    {item.used.map((u) => (
                      <li key={u}><code className="mono break-all rounded-sm bg-[#191919] px-1.5 py-0.5 text-[0.75rem] text-[var(--acid)]">{u}</code></li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </li>
  )
}

export default function References() {
  const [q, setQ] = useState('')
  const [group, setGroup] = useState('All')
  const text = (it) => [it.title, it.detail, it.note, it.status, ...(it.facts || []), ...(it.used || [])].join(' ').toLowerCase()
  const total = REFERENCES.reduce((n, g) => n + g.items.length, 0)
  const linked = REFERENCES.reduce((n, g) => n + g.items.filter((i) => i.url).length, 0)

  return (
    <div>
      {/* summary */}
      <div className="mb-8 grid grid-cols-2 gap-px overflow-hidden rounded-xl border-2 border-[#191919] bg-[#191919] sm:grid-cols-6">
        {[['Total', total], ...REFERENCES.map((g) => [g.group, g.items.length])].map(([k, v], i) => (
          <div key={k} className="p-4" style={{ background: i === 0 ? 'var(--acid)' : 'var(--surface-1)', color: i === 0 ? '#191919' : undefined }}>
            <span className="wide block text-3xl font-black leading-none">{v}</span>
            <span className="mono mt-1 block text-[0.6875rem] font-bold uppercase opacity-80">{k}</span>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-2" role="tablist">
          {['All', ...REFERENCES.map((g) => g.group)].map((g) => (
            <button key={g} role="tab" aria-selected={group === g} onClick={() => setGroup(g)}
                    className="mono rounded-md border-2 px-3 py-1.5 text-[0.75rem] font-bold uppercase transition-all"
                    style={{ borderColor: group === g ? '#191919' : 'var(--border-strong)', background: group === g ? 'var(--acid)' : 'var(--surface-1)', color: group === g ? '#191919' : undefined }}>
              {g}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 rounded-md border-2 px-3 py-1.5" style={{ borderColor: 'var(--border-strong)', background: 'var(--surface-1)' }}>
          <Search size={14} className="text-ink-muted" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={`Search ${total} references`} aria-label="Search references"
                 className="mono w-48 bg-transparent text-[0.8125rem] text-ink-primary outline-none placeholder:text-ink-muted" />
        </label>
      </div>
      <p className="mono mt-3 text-[0.6875rem] text-ink-muted">
        {linked} entries link to the original source · open ▾ on an entry for key facts and where it is used in the code · search also looks inside the details
      </p>

      <div className="mt-8 space-y-10">
        {REFERENCES.filter((g) => group === 'All' || g.group === group).map((g) => {
          const items = g.items.filter((it) => text(it).includes(q.toLowerCase()))
          if (!items.length) return null
          return (
            <section key={g.group} aria-label={g.group}>
              <div className="flex items-center gap-3">
                <span className="h-4 w-4 rounded-sm border-2 border-[#191919]" style={{ background: g.color }} />
                <h3 className="wide text-xl font-black uppercase">{g.group}</h3>
                <span className="mono text-[0.75rem] text-ink-muted">{items.length}</span>
              </div>
              <ol className="mt-4 overflow-hidden rounded-xl border-2 border-[#191919]" style={{ boxShadow: `6px 6px 0 ${g.color}` }}>
                {items.map((it, i) => <Entry key={it.title} item={it} index={i} />)}
              </ol>
            </section>
          )
        })}
      </div>
      <p className="mono mt-6 text-[0.6875rem] text-ink-muted">
        SRC docs/models/MODEL_CARD.md · docs/research/DATASETS.md · docs/research/EVALUATION.md · backend/requirements*.txt · README.md.
        Cite each dataset as its own card asks.
      </p>
    </div>
  )
}
