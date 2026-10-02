# 6. Frontend (Next.js + React)
Code: `web/`. Run with `npm run dev` and open http://localhost:3000.

## Structure
```
web/
├── app/
│   ├── layout.js        HTML shell, font, page title, shared Header
│   ├── page.js          Predictor page: state, API calls, layout of the dashboard
│   ├── accuracy/page.js Model accuracy page (GET /evaluation)
│   └── globals.css      futuristic dark theme: color tokens, glass panels, hero, 3D fallback
├── components/
│   ├── Scene3D.jsx      Three.js 3D background: crystal, orbit rings, particles, grid floor
│   ├── Hero.jsx         big "DevAscend" title, key stats and buttons on the home page
│   ├── Header.jsx       logo, navigation (Predictor / Model accuracy), API + Cassandra status
│   ├── LearningGuide.jsx learn-next topics, "things juniors learn too late", market trends
│   ├── Form.jsx         ♻ reusable form wrapper (title, submit button, loading, error)
│   ├── Input.jsx        ♻ reusable field: label + text/number/select + hint/error
│   ├── SkillPicker.jsx  searchable multi-select with chips
│   ├── GitHubImport.jsx bonus: fetch languages from a GitHub username
│   ├── ProfileForm.jsx  the profile form built from Form + Input (+ validation)
│   ├── LevelBadge.jsx   output 1: score ring, level, market value, probability bars
│   ├── GoalCards.jsx    output 3: time to goal + checkpoints (6m / 1y / 2y / 3y)
│   ├── GrowthChart.jsx  output 2: Recharts line chart, two scenarios, score/value toggle
│   ├── SkillGapBars.jsx output 4: bars = higher-level devs, tick = your level
│   ├── WhatIfList.jsx   output 5: table of boosts
│   ├── Roadmap.jsx      output 6: vertical month-by-month timeline
│   ├── ModelInfo.jsx    collapsible table comparing the algorithms
│   └── HistoryTable.jsx recent predictions from Cassandra
└── lib/api.js           all fetch calls to the backend + small helpers
```

## Reusable Form and Input
- `Form` handles the submit event with `event.preventDefault()`, so the page doesn't reload. It also shows the loading spinner and error message, so every form behaves the same way.
- `Input` renders a label and an input or select, and calls `onChange(name, value)`. **One** handler can then update any field:
  ```js
  const set = (name, value) => setForm((f) => ({ ...f, [name]: value }));
  <Input label="Years coding" name="years_code" type="number" value={form.years_code} onChange={set} />
  ```
- Numbers are converted with `Number()` inside Input, so the parent always receives numbers.

## State and data flow (`page.js`)
- `useEffect` on load fetches `/options` (dropdown lists), `/health` (status dots), `/model-info` and `/history`.
- `form` state holds the profile. `ProfileForm` validates it (for example, years professional can't exceed years coding) before calling `runPrediction`.
- `runPrediction` calls `/predict` and `/analysis` together, then `/growth`, and stores the results in `result`. React re-renders the dashboard.

## Futuristic 3D design (Three.js)
`Scene3D.jsx` draws a WebGL scene **behind** every page (`position: fixed`, `pointer-events: none`, so it never blocks clicks):
- a glowing **wireframe crystal** (icosahedron) with a "breathing" violet core = the heart of DevAscend
- three tilted **orbit rings** with small satellites moving along them
- a **star field** of 2,200 cyan/violet particles, plus 420 particles that keep **rising upward** (growth = "ascend")
- a perspective **grid floor** that slides towards the viewer
- **mouse parallax** (the camera eases towards the pointer) and the scene lifts as you scroll

How it is built, in viva terms:
- `import("three")` runs inside `useEffect`, so Three.js only loads in the browser, never during server rendering.
- Every frame runs inside `requestAnimationFrame`. It **pauses when the tab is hidden** (saves battery), and with the OS **reduce-motion** setting it draws only one still frame.
- On unmount it disposes every geometry, material and the renderer, so there are no memory leaks.
- **WebGL fallback:** some browsers or locked-down PCs have WebGL disabled. The component checks for WebGL first, and if it's missing it shows a pure-CSS animated crystal and rings instead. The page never breaks.

The UI on top uses **glassmorphism**: semi-transparent panels with `backdrop-filter: blur(14px)`, a neon cyan → violet gradient for the brand, buttons and title, and a soft glow on hover.

## Charts and design
- **Recharts** `LineChart` uses one y-axis and two lines: cyan solid for *with roadmap*, orange dashed for *experience only*. A toggle switches between level score and market value. Hovering shows a tooltip with both values.
- Colors are CSS variables (design tokens) at the top of `globals.css`: one futuristic dark theme, so every component uses the same cyan, violet and orange.
- The layout is responsive: the form sits beside the dashboard on desktop and stacks on top on mobile.

## Pages
- **/** (Predictor): the form and every prediction output, including the learning guide with clickable free resources.
- **/accuracy** (Model accuracy): metric tiles (Accuracy, F1, MAE, RMSE, R², % error, within ±20%), model vs baseline bars, the confusion matrix as a heat grid, errors per salary band, country and level, and 12 real test developers with predicted vs actual values.

In the App Router, a folder inside `app/` becomes a URL: `app/accuracy/page.js` is served at `/accuracy`.

## Bonus: GitHub import
`GitHubImport.jsx` calls the public GitHub REST API, `GET https://api.github.com/users/<name>/repos`, and reads each repo's main language. It maps names like `Shell` → `Bash/Shell` and adds them to the skills. No login is needed (limit: 60 requests per hour).

## API address
`web/.env.local` contains `NEXT_PUBLIC_API_URL=http://localhost:8000`. Variables starting with `NEXT_PUBLIC_` are available in browser code.
