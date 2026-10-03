"""Demo video for Advance (Qloo Agentic Hackathon 2026). No presenter; clips are real recordings (video/record.py).

    ~/.venvs/video/bin/python ~/Desktop/KHLab/hack-nation/kit/video/render.py video/script.py --length-only
    ~/.venvs/video/bin/python ~/Desktop/KHLab/hack-nation/kit/video/render.py video/script.py --out video/demo.mp4 --max-seconds 135
"""

VOICE = "en-US-AndrewNeural"

SCENES = [
    ("card:problem",
     "Before a show goes on sale, a promoter decides where to play, who opens, which room, where the after party is, "
     "and who sponsors. Today that comes from ticket history and a genre chart. Neither one knows what this "
     "particular audience loves."),
    ("clip:phoebe",
     "Advance asks Qloo's taste graph. Type a headliner and a city. A language model, Apertus seventy B, turns the "
     "sentence into a plan, and Qloo answers each question for this headliner's audience: where to play, who opens, "
     "which room in Chicago, and where fans go after. Every line carries Qloo's affinity score and the request "
     "behind it."),
    ("card:agent",
     "The model writes the advance notes, but its schema only allows names that Qloo returned, so it cannot "
     "recommend anything that is not in the brief. If the model is down, a pattern planner and a template take over, "
     "and the page says so."),
    ("clip:metallica",
     "Name a country, and routing stays inside it. Metallica in Berlin and Munich: German cities, Berlin's arenas "
     "and halls, the bars fans pick, and brands like Fender and Gibson."),
    ("card:proof",
     "Does taste find the acts promoters actually book? We took a hundred and fifteen real tours with their support "
     "acts, and gave Advance only the headliner. Qloo's taste list puts twenty six real openers in its top ten. A genre "
     "chart puts one. In the top hundred, a hundred and nine against seventeen."),
    ("card:api",
     "Along the way we mapped where the API fails silently: a take above fifty, genre tags that need a music segment, "
     "and bars that are really hotel lobbies. Each one is guarded by a test, and the whole backtest replays offline "
     "from recorded responses."),
    ("card:outro",
     "Advance. The tour advance, from your audience's taste. Live now, and open source."),
]

CARDS = {
    "problem": """<h1>Five calls a promoter makes by gut</h1>
    <p class=sub>Before a show goes on sale</p>
    <table>
      <tr><td><b>Where to play</b></td><td>routing</td></tr>
      <tr><td><b>Who opens</b></td><td>the support act</td></tr>
      <tr><td><b>Which room</b></td><td>the venue</td></tr>
      <tr><td><b>After the show</b></td><td>partners for the after-party</td></tr>
      <tr><td><b>Who sponsors</b></td><td>brand partners</td></tr>
    </table>
    <p class=foot>Inputs today: ticket history (only where you have played) and a genre chart (what is popular, not what this audience loves).</p>""",
    "agent": """<h1>An agent that cannot make things up</h1>
    <p class=sub>Plan → Qloo → advice, each step labelled on the page</p>
    <table>
      <tr><td><b>Plan</b></td><td>Apertus 70B fills a JSON schema: headliner, ≤3 cities, country, opener size</td></tr>
      <tr><td><b>Ask Qloo</b></td><td>/v2/insights per question, parameters checked against an allow-list</td></tr>
      <tr><td><b>Advise</b></td><td>schema enum = only names Qloo returned</td></tr>
      <tr><td><b>Fallback</b></td><td>pattern planner + template; the trace says which step answered</td></tr>
    </table>""",
    "proof": """<h1>Checked on 115 real tours</h1>
    <p class=sub>Where do the openers promoters actually booked (2023–2025) land? 619 openers Qloo knows.</p>
    <table>
      <tr><th></th><th>Qloo taste (Advance)</th><th>Genre chart</th></tr>
      <tr><td>in the top 10</td><td class="ok big">26</td><td class=big>1</td></tr>
      <tr><td>in the top 25</td><td class="ok big">48</td><td class=big>4</td></tr>
      <tr><td>in the top 100</td><td class="ok big">109</td><td class=big>17</td></tr>
    </table>
    <p class=foot>Ranked 1st–2nd: Sleeping with Sirens for Pierce the Veil · Modest Mouse for Weezer · Wild Rivers for Noah Kahan · Keyshia Cole for Brandy</p>""",
    "api": """<h1>Where the API fails silently</h1>
    <p class=sub>Found against the live hackathon API; each one has a test</p>
    <table>
      <tr><td><code>take</code> &gt; 50</td><td>400 → Advance pages</td></tr>
      <tr><td><code>urn:tag:genre:pop_rock</code></td><td>empty 200 → needs <code>urn:tag:genre:music:pop_rock</code></td></tr>
      <tr><td>places with no category</td><td>airports and skyscrapers → venue and bar categories</td></tr>
      <tr><td>“bar”</td><td>includes hotel lobbies → <code>filter.exclude.tags</code></td></tr>
    </table>
    <p class=foot>QLOO_MODE=replay reproduces the backtest from 999 recorded responses, no key, no network.</p>""",
    "outro": """<h1>Advance<span style="color:#714cb6">.</span></h1>
    <p class=sub>The tour advance, from your audience's taste.</p>
    <pre>khlab-advance.onrender.com
github.com/bisale24-ops/advance   (MIT)</pre>
    <p class=foot>KHLab · Qloo Agentic Hackathon 2026 · built on Qloo's Taste AI</p>""",
}

CLIPS = {
    "phoebe": ("clips/phoebe.webm", 3),
    "metallica": ("clips/metallica.webm", 21),
}
