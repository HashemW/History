"""Build a self-contained study folder for Yale RLST 145 from downloaded Open Yale Courses pages."""
import codecs, html, os, re, sys, urllib.parse, urllib.request
import concurrent.futures as cf
from html.parser import HTMLParser

RAW, OUT = sys.argv[1], sys.argv[2]
SLUG = 'old-testament-yale-rlst145'
CDIR = os.path.join(OUT, SLUG)
LDIR = os.path.join(CDIR, 'lectures')
HDIR = os.path.join(CDIR, 'handouts')
for d in (CDIR, LDIR, HDIR):
    os.makedirs(d, exist_ok=True)

BASE = 'https://oyc.yale.edu'
COURSE_URL = BASE + '/religious-studies/rlst-145'
UA = {'User-Agent': 'Mozilla/5.0'}
LICENSE = ('Lecture content © Yale University, from [Open Yale Courses](https://oyc.yale.edu), licensed under '
           '[CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/us/).')


def _fallback(e):
    return (e.object[e.start:e.end].decode('cp1252', 'replace'), e.end)


codecs.register_error('cpfb', _fallback)


def load(name):
    with open(os.path.join(RAW, name), 'rb') as f:
        return f.read().decode('utf-8', 'cpfb')


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text.rstrip() + '\n')


# ---------------------------------------------------------------- HTML -> Markdown
class MD(HTMLParser):
    HEAD = {'h1': '##', 'h2': '##', 'h3': '###', 'h4': '####', 'h5': '#####'}
    WRAP = ('strong', 'b', 'em', 'i', 'a')
    NORM = {'b': 'strong', 'i': 'em'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.wrap, self.lists = [[]], [], []

    @property
    def buf(self):
        return self.stack[-1]

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('p', 'div', 'table', 'tr'):
            self.buf.append('\n\n')
        elif tag == 'br':
            self.buf.append('\n')
        elif tag in self.HEAD:
            self.buf.append('\n\n' + self.HEAD[tag] + ' ')
        elif tag in self.WRAP:
            self.wrap.append((self.NORM.get(tag, tag), a.get('href')))
            self.stack.append([])
        elif tag in ('ul', 'ol'):
            self.lists.append(tag)
            self.buf.append('\n')
        elif tag == 'li':
            self.buf.append('\n' + ('1. ' if self.lists and self.lists[-1] == 'ol' else '- '))
        elif tag == 'sup':
            self.buf.append('<sup>')
        elif tag == 'blockquote':
            self.buf.append('\n\n> ')

    def handle_endtag(self, tag):
        if tag in ('p', 'div', 'table', 'tr') or tag in self.HEAD:
            self.buf.append('\n\n')
        elif tag in self.WRAP:
            n = self.NORM.get(tag, tag)
            if not any(t == n for t, _ in self.wrap):
                return
            while True:
                t, href = self.wrap.pop()
                inner = ''.join(self.stack.pop())
                if t == n:
                    break
                self.buf.append(inner)
            core = inner.strip()
            if not core:
                self.buf.append(inner)
                return
            lead = inner[:len(inner) - len(inner.lstrip())]
            trail = inner[len(inner.rstrip()):]
            if t == 'strong':
                s = f'**{core}**'
            elif t == 'em':
                s = f'*{core}*'
            elif href and not href.startswith(('#', 'javascript')):
                s = f'[{core}]({urllib.parse.urljoin(BASE, href)})'
            else:
                s = core
            self.buf.append(lead + s + trail)
        elif tag in ('ul', 'ol'):
            if self.lists:
                self.lists.pop()
            self.buf.append('\n\n')
        elif tag == 'sup':
            self.buf.append('</sup>')

    def handle_data(self, d):
        self.buf.append(re.sub(r'\s+', ' ', d))

    def result(self):
        while len(self.stack) > 1:
            inner = ''.join(self.stack.pop())
            self.buf.append(inner)
        s = ''.join(self.stack[0])
        s = re.sub(r'[ \t]+\n', '\n', s)
        s = re.sub(r'\n[ \t]+', '\n', s)
        s = re.sub(r'\n{3,}', '\n\n', s)
        return s.strip()


def md(h):
    p = MD()
    p.feed(h)
    p.close()
    return p.result()


def hms(sec):
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


def yt(vid, t=None):
    return f'https://www.youtube.com/watch?v={vid}' + (f'&t={int(t)}s' if t is not None else '')


# ---------------------------------------------------------------- Bible readings (from Yale's assignment lists)
BOOKS = {  # display -> (Sefaria name, BibleGateway name)
    '1 Samuel': ('I_Samuel', '1 Samuel'), '2 Samuel': ('II_Samuel', '2 Samuel'),
    '1 Kings': ('I_Kings', '1 Kings'), '2 Kings': ('II_Kings', '2 Kings'),
    'Song of Songs': ('Song_of_Songs', 'Song of Songs'),
}
SECTION = 'for section discussion'
SAME = {3: 2, 5: 4, 7: 6, 11: 10, 14: 13}
READINGS = {
    1: [('Genesis', '1-4')],
    2: [('Genesis', '1-4')],
    4: [('Genesis', '5-11'), ('Genesis', '1-3', SECTION)],
    6: [('Genesis', '12-50'), ('Exodus', '1-4'), ('Genesis', '22', SECTION)],
    8: [('Exodus', '5-24, 32'), ('Exodus', '25-40', 'skim: construction of the sanctuary'),
        ('Leviticus', '1-8', 'skim: sacrificial system'), ('Leviticus', '11-17', 'skim: dietary laws and impurity system'),
        ('Numbers', '11-14, 16, 19-20, 25')],
    9: [],
    10: [('Leviticus', '18-20, 24:10-23, 25', 'legal texts'), ('Numbers', '35', 'legal texts'),
         ('Deuteronomy', '15, 17, 19, 22, 25', 'legal texts'), ('Deuteronomy', '1-14, 27-34', 'narrative texts')],
    12: [('Joshua', '1-13, 20, 23-24'), ('Judges', '1-8, 13-16, 19-21')],
    13: [('1 Samuel', '1-31', 'the whole book'), ('2 Samuel', '1-24', 'the whole book'),
         ('1 Kings', '3, 11-12, 16:29-19:21, 21-22'), ('2 Kings', '8:25-10:36, 17-25')],
    15: [('Amos', '1-9')],
    16: [('Amos', '1-9')],
    17: [('Hosea', '1-14'), ('Isaiah', '1-12, 28-33, 36-39')],
    18: [('Micah', '1-7'), ('Nahum', '1-3'), ('Habakkuk', '1-3'), ('Zephaniah', '1-3')],
    19: [('Jeremiah', '1-8, 18-21, 23, 25-45, 52'), ('Ezekiel', '1:1-5:4, 8-11, 16-18, 23, 28, 33, 36-37, 40, 47'),
         ('Isaiah', '40-42, 49-55', '"Second Isaiah"')],
    20: [('Lamentations', '1-5'),
         ('Proverbs', '1-13, 31', 'Yale\'s list says "32", but Proverbs has only 31 chapters, so ch. 31 is linked'),
         ('Job', '1-11, 21-31, 38-42'), ('Ecclesiastes', '1-12')],
    21: [('Psalms', '1, 2, 8, 19, 21-24, 32, 37, 44-46, 49, 52, 55, 72-74, 78-80, 90, 93, 96-99, 103-106, 109, '
                    '110, 112, 114, 115, 118, 119, 128, 131, 136, 137, 139, 150'), ('Song of Songs', '1-8')],
    22: [('Ezra', '1-10'), ('Nehemiah', '10, 13')],
    23: [('Isaiah', '56-66', '"Third Isaiah"'),
         ('Joel', '1-4', 'Hebrew numbering; English Bibles split the same text into 3 chapters'), ('Daniel', '1-12')],
    24: [('Esther', '1-9'), ('Ruth', '1-4'), ('Jonah', '1-4')],
}
for k, v in SAME.items():
    READINGS[k] = READINGS[v]


def sefaria(book, seg):
    return f'https://www.sefaria.org/{BOOKS.get(book, (book,))[0]}.{seg.replace(":", ".")}?lang=en'


def biblegateway(book, seg):
    if book == 'Joel' and seg == '1-4':
        seg = '1-3'
    q = urllib.parse.quote_plus(f'{BOOKS.get(book, (book, book))[1]} {seg}')
    return f'https://www.biblegateway.com/passage/?search={q}&version=NRSVUE'


def bible_table(n):
    rows = READINGS.get(n, [])
    if not rows:
        return '_No Bible chapters this time. This lecture\'s readings are essays (see below)._\n'
    out = ['| Passage | Read it: JPS translation (same as the Jewish Study Bible) | Alternate: NRSVue |',
           '|---|---|---|']
    for book, segs, *note in rows:
        segs_l = [x.strip() for x in segs.split(',')]
        label = f'**{book}** {segs}' + (f' <br>_({note[0]})_' if note else '')
        sef = ' · '.join(f'[{x}]({sefaria(book, x)})' for x in segs_l)
        bg = ' · '.join(f'[{x}]({biblegateway(book, x)})' for x in segs_l)
        out.append(f'| {label} | {sef} | {bg} |')
    return '\n'.join(out) + '\n'


def bible_summary(n):
    if n == 9:
        return 'Essays: purity & the sanctuary'
    parts = []
    for book, segs, *note in READINGS.get(n, []):
        if note and note[0] == SECTION:
            continue
        parts.append(f'{book} (selections)' if len(segs) > 24 else f'{book} {segs}')
    return '; '.join(parts)


# ---------------------------------------------------------------- where to find the non-Bible readings
IA = 'https://archive.org/details/'


def ia_search(q):
    return 'https://archive.org/search?query=' + urllib.parse.quote_plus(q)


def scholar(q):
    return 'https://scholar.google.com/scholar?q=' + urllib.parse.quote_plus(q)


FREE = {  # public-domain / open translations of the Pritchard selections (checked below, dropped if dead)
    'enuma': ('*Enuma Elish* ("The Creation Epic"), L. W. King translation', 'https://sacred-texts.com/ane/enuma.htm'),
    'gilg': ('*The Epic of Gilgamesh*, R. Campbell Thompson translation', 'https://sacred-texts.com/ane/eog/index.htm'),
    'flood': ('Sumerian Flood Story ("The Deluge"), Oxford ETCSL translation', 'https://etcsl.orinst.ox.ac.uk/section1/tr174.htm'),
    'hamm': ('*The Code of Hammurabi*, L. W. King translation (Yale Avalon Project)', 'https://avalon.law.yale.edu/ancient/hamframe.asp'),
}


def alive(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except Exception:
        return False


with cf.ThreadPoolExecutor(8) as ex:
    ok = dict(zip(FREE, ex.map(lambda k: alive(FREE[k][1]), FREE)))
print('free-text links alive:', ok)


def free(*keys):
    links = [f'[{FREE[k][0]}]({FREE[k][1]})' for k in keys if ok.get(k)]
    return (' · Free online versions: ' + ' · '.join(links)) if links else ''


SOURCES = [
    (r'JSB|Jewish Study Bible',
     f'**The Jewish Study Bible** (Oxford, 2004), the course textbook. The "Introduction to …" and essay readings '
     f'(cited as *JSB* pp. …) are in this book → [borrow it free on Internet Archive]({IA}jewishstudybible0000unse_x6n0) '
     f'(free account; same 2004 edition the course used)'),
    (r'Pritchard',
     f'**Pritchard, ed., *The Ancient Near East, Vol. 1: An Anthology of Texts and Pictures*** → '
     f'[borrow free on Internet Archive]({IA}ancientneareasta00prit)'),
    (r'Creation Epic|Gilgamesh|Deluge', '**The Pritchard myths for this lecture**' + free('enuma', 'gilg', 'flood')),
    (r'Hammurabi', '**The Pritchard law codes for this lecture**' + free('hamm')),
    (r'Ancient Near Eastern Texts Relating',
     f'**Pritchard, ed., *Ancient Near Eastern Texts Relating to the Old Testament* (ANET)** → '
     f'[search Internet Archive]({ia_search("Ancient Near Eastern Texts Relating to the Old Testament")})'),
    (r'Kaufmann',
     f'**Kaufmann, *The Religion of Israel*** (Schocken, 1972) → [borrow on Internet Archive]({IA}religionofisrael0000kauf_j7j0)'),
    (r'Habel',
     f'**Habel, *Literary Criticism of the Old Testament*** (1971) → no free online copy found yet; borrow it free through a public library (see [notes](../TODO-free-readings.md))'),
    (r'Boyarin', f'**Boyarin, *Carnal Israel*** → [search Internet Archive]({ia_search("Carnal Israel Boyarin")})'),
    (r'Pagels',
     f'**Pagels, *Adam, Eve, and the Serpent*** → [search Internet Archive]({ia_search("Adam, Eve, and the Serpent Pagels")})'),
    (r'Trible',
     f'**Trible, "Depatriarchalizing in Biblical Interpretation"** (*JAAR* 41, 1973) → '
     f'[borrow the free reprint](https://archive.org/details/jewishwomannewpe0000kolt/page/217/mode/2up) in Koltun, *The Jewish Woman* (1976), pp. 217–240'),
    (r'Out of the Garden',
     f'***Out of the Garden: Women Writers on the Bible*** (Buchmann & Spiegel, eds.) → '
     f'[search Internet Archive]({ia_search("Out of the Garden Women Writers on the Bible")})'),
    (r'Auerbach',
     f'**Auerbach, "Odysseus\' Scar," in *Mimesis*** → [search Internet Archive]({ia_search("Mimesis Auerbach")})'),
    (r'Alter, Robert',
     f'**Alter, *The Art of Biblical Narrative*** (1981) → no free online copy found yet; borrow it free through a public library (see [notes](../TODO-free-readings.md))'),
    (r'Greenstein',
     f'**Preminger & Greenstein, eds., *The Hebrew Bible in Literary Criticism*** → '
     f'[search Internet Archive]({ia_search("The Hebrew Bible in Literary Criticism Preminger Greenstein")})'),
    (r'Milgrom',
     f'**Milgrom, "Israel\'s Sanctuary: The Priestly \'Picture of Dorian Gray\'"** (*Revue Biblique*) → '
     f'[find the article]({scholar("Milgrom Israel Sanctuary Priestly Picture of Dorian Gray")})'),
    (r'Anchor Bible Dictionary',
     f'***The Anchor Bible Dictionary*** → [search Internet Archive]({ia_search("Anchor Bible Dictionary")})'),
    (r'Sternberg',
     f'**Sternberg, *The Poetics of Biblical Narrative*** → [search Internet Archive]({ia_search("Poetics of Biblical Narrative Sternberg")})'),
    (r'Encyclopedia of Religion',
     f'***The Encyclopedia of Religion*** (Eliade, ed., 1987), vol. 12 → '
     f'[search Internet Archive]({ia_search("Encyclopedia of Religion Eliade")})'),
    (r'Reis', f'**Reis, *Reading the Lines*** → [search Internet Archive]({ia_search("Reading the Lines Reis Hebrew Bible")})'),
    (r'Kierkegaard',
     f'**Kierkegaard, *Fear and Trembling*** → [search Internet Archive]({ia_search("Kierkegaard Fear and Trembling")})'),
]

# ---------------------------------------------------------------- parse lecture pages
lectures, pdfs = [], {}


def block(s, start_pat, end_pats):
    m = re.search(start_pat, s)
    if not m:
        return ''
    rest = s[m.end():]
    ends = [i for i in (rest.find(p) for p in end_pats) if i >= 0]
    return rest[:min(ends)] if ends else rest


for n in range(1, 25):
    s = load(f'lecture-{n}.html')
    title = html.unescape(re.search(r'<title>RLST 145 - Lecture \d+ - (.*?) \| Open Yale Courses', s, re.S).group(1)).strip()
    m = re.search(r'(?s)session-full__body-label">\s*Overview\s*</h3>(.*?)</div>', s)
    overview = md(m.group(1)) if m else ''
    names = [md(x) for x in re.findall(r'field-session-chapters-name"><div class="field-content">(.*?)</div>', s, re.S)]
    times = re.findall(r'field-session-chapter-start-time"><div class="field-content">(\d+)</div>', s)
    vid = re.search(r'youtube\.com/embed/([\w-]+)', s).group(1)
    mp3 = urllib.parse.urljoin(BASE, re.search(r'href="([^"]+\.mp3)"', s).group(1))
    tr = block(s, r'<div id="inline_content">', ['<a href="#transcript-top">Back to Top</a>'])
    tr = re.sub(r'(?s)<h1[^>]*>.*?</h1>', '', tr, count=1)
    tr = re.sub(r'(?s)<h2[^>]*>.*?</h2>', '', tr, count=1)
    tr = md(tr)
    tr = re.sub(r'(?m)^(#{2,4} .*?)\s*\[(\d{2}):(\d{2}):(\d{2})\]\s*$',
                lambda m: f'{m.group(1)} [▶ {m.group(2)}:{m.group(3)}:{m.group(4)}]'
                          f'({yt(vid, int(m.group(2)) * 3600 + int(m.group(3)) * 60 + int(m.group(4)))})', tr)
    assign_html = block(s, r'<h2>Assignment</h2>', ['block-views-blocksession-resource-files', '<footer', '>Footer<'])
    assignment = md(assign_html)
    res_html = block(s, r'<h2>Resources</h2>', ['<footer', '>Footer<'])
    resources = []
    for row in res_html.split('views-row')[1:]:
        m = re.search(r'href="([^"]+\.pdf)"', row)
        if m:
            label = re.sub(r'\s*\[PDF\]\s*', '', html.unescape(re.sub(r'(?s)<[^>]+>', ' ', row.split('>', 1)[1])))
            label = re.sub(r'\s+', ' ', label).strip(' >"')
            fn = m.group(1).rsplit('/', 1)[1]
            resources.append((label, fn))
            pdfs[fn] = urllib.parse.urljoin(BASE, m.group(1))
    lectures.append(dict(n=n, title=title, overview=overview, chapters=list(zip(names, times)), vid=vid, mp3=mp3,
                         transcript=tr, assignment=assignment, assign_text=html.unescape(re.sub(r'<[^>]+>', ' ', assign_html)),
                         resources=resources, url=f'{COURSE_URL}/lecture-{n}'))

exam = load('exam-1.html')
exam_pdf = re.search(r'href="([^"]+\.pdf)"', exam).group(1)
pdfs[exam_pdf.rsplit('/', 1)[1]] = urllib.parse.urljoin(BASE, exam_pdf)


# ---------------------------------------------------------------- download handouts
def fetch(item):
    fn, url = item
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(os.path.join(HDIR, fn), 'wb') as f:
        f.write(data)
    return fn, len(data), data[:4] == b'%PDF'


with cf.ThreadPoolExecutor(8) as ex:
    for fn, size, ispdf in ex.map(fetch, pdfs.items()):
        print(f'  pdf {fn}: {size} bytes, valid={ispdf}')

# ---------------------------------------------------------------- write lecture pages
for L in lectures:
    L['file'] = f"{L['n']:02d}-" + re.sub(r'[^a-z0-9]+', '-', L['title'].lower()).strip('-')[:60].rstrip('-') + '.md'

for k, L in enumerate(lectures):
    prev = lectures[k - 1] if k else None
    nxt = lectures[k + 1] if k + 1 < len(lectures) else None
    nav = ' · '.join(x for x in [
        f"[← Lecture {prev['n']}]({prev['file']})" if prev else '',
        '[Course home](../README.md)',
        f"[Lecture {nxt['n']} →]({nxt['file']})" if nxt else ''] if x)
    chapters = '\n'.join(f'{i}. [▶ {hms(t)}]({yt(L["vid"], t)}) {name}' for i, (name, t) in enumerate(L['chapters'], 1))
    found = [text for pat, text in SOURCES if re.search(pat, L['assign_text'])]
    where = '\n'.join(f'- {t}' for t in found) or '- _Everything for this lecture is in the Bible table above._'
    res = '\n'.join(f'- 📄 [{label}](../handouts/{fn})' for label, fn in L['resources'])
    page = f"""# Lecture {L['n']}: {L['title']}

{nav}

**Course:** Introduction to the Old Testament (Hebrew Bible), RLST 145, Yale · Prof. Christine Hayes

| | |
|---|---|
| ▶️ **Watch** | [YouTube video]({yt(L['vid'])}) |
| 🎧 **Listen** | [MP3 audio]({L['mp3']}) |
| 📝 **Read** | [Full transcript ↓](#-full-transcript) |
| 🏛️ **Source** | [Yale lecture page]({L['url']}) |

[![Watch Lecture {L['n']} on YouTube](https://img.youtube.com/vi/{L['vid']}/hqdefault.jpg)]({yt(L['vid'])})

## Overview

{L['overview']}

## Lecture chapters (click a time to jump into the video)

{chapters}

## 📚 Readings for this lecture

### Bible passages

{bible_table(L['n'])}
### Where to find the other readings

{where}

<details>
<summary>Yale's original assignment list (word for word)</summary>

{L['assignment']}

</details>
"""
    if res:
        page += f'\n## Handouts\n\n{res}\n'
    page += f"\n## 📝 Full transcript\n\n{L['transcript']}\n\n---\n\n{nav}\n\n<sub>{LICENSE}</sub>\n"
    write(os.path.join(LDIR, L['file']), page)

# ---------------------------------------------------------------- course README
course = load('course.html')
rows = []
for L in lectures:
    rows.append(f"| {L['n']} | [{L['title']}](lectures/{L['file']}) | {bible_summary(L['n'])} | "
                f"[▶ Video]({yt(L['vid'])}) | [🎧 MP3]({L['mp3']}) |")
    if L['n'] == 11:
        rows.append('| — | **Midterm exam** | Review: [review sheet](handouts/midterm-review.pdf) | '
                    '[📄 Exam (PDF)](handouts/midterm-exam.pdf) | |')
handouts = []
for L in lectures:
    for label, fn in L['resources']:
        handouts.append(f"| [{label}](handouts/{fn}) | [Lecture {L['n']}](lectures/{L['file']}) |")
handouts.append(f"| [Midterm Exam](handouts/midterm-exam.pdf) | [Exam page]({COURSE_URL}/exam-1) |")
progress = '\n'.join(f"- [ ] [Lecture {L['n']}: {L['title']}](lectures/{L['file']})"
                     + ('\n- [ ] Midterm: try the [exam](handouts/midterm-exam.pdf) using the '
                        '[review sheet](handouts/midterm-review.pdf)' if L['n'] == 11 else '')
                     for L in lectures)

readme = f"""# Introduction to the Old Testament (Hebrew Bible)

**Yale University, RLST 145** · Professor **Christine Hayes** · Recorded Fall 2006 · 24 lectures
Source: [Open Yale Courses]({COURSE_URL})

> This course examines the Old Testament (Hebrew Bible) as an expression of the religious life and thought of
> ancient Israel, and a foundational document of Western civilization. A wide range of methodologies, including
> source criticism and the historical-critical school, tradition criticism, redaction criticism, and literary and
> canonical approaches are applied to the study and interpretation of the Bible. Special emphasis is placed on the
> Bible against the backdrop of its historical and cultural setting in the Ancient Near East.

Everything for the course is in this folder: every lecture video, audio file and full transcript, every reading
with a direct link, and every handout and exam as a PDF.

## How to study each lecture

1. **Open the lecture page** (click its title below).
2. **Do the readings first.** Each lecture page has a table of the Bible chapters with one-click links, plus
   where to find the textbook pages.
3. **Watch the lecture** (YouTube) or **listen** (MP3). Use the chapter timestamps to jump around.
4. **Review with the transcript**, which is on the same page below the readings.

## Lectures

| # | Lecture (readings + transcript) | Bible reading | Watch | Listen |
|---|---|---|---|---|
{chr(10).join(rows)}

## Textbooks

The course uses two books. Both can be borrowed free from the Internet Archive (you need a free account):

| Book | What it's for | Get it |
|---|---|---|
| **The Jewish Study Bible** (Berlin & Brettler, eds., Oxford 2004) | The Bible text (JPS translation), plus the "Introduction to …" and essay readings cited as *JSB* pp. … | [Borrow (2004 ed.)]({IA}jewishstudybible0000unse_x6n0) |
| **The Ancient Near East, Vol. 1** (Pritchard, ed., Princeton 1958) | Myths and law codes from Israel's neighbors (Enuma Elish, Gilgamesh, Hammurabi …) | [Borrow]({IA}ancientneareasta00prit) |

**You don't need the physical Bible.** Every Bible passage on the lecture pages links to
[Sefaria](https://www.sefaria.org/texts/Tanakh), which has the JPS translation used in the Jewish Study Bible,
and to [BibleGateway](https://www.biblegateway.com/versions/New-Revised-Standard-Version-Updated-Edition-NRSVue-Bible/)
for the NRSVue, the standard translation used by scholars.

## Handouts & exams

| Handout | Goes with |
|---|---|
{chr(10).join(handouts)}

## Syllabus (as given at Yale)

**Requirements**
1. A midterm exam (after Lecture 11).
2. A paper (about 10 pages) on a selected biblical passage. The paper develops an interpretation of the passage
   while comparing and critiquing a range of traditional and scholarly interpretations. See the
   [final paper assignment](handouts/final-paper-assignment.pdf).
3. A final exam covering lectures and readings. See the [final exam review sheet](handouts/final-exam-review-2006.pdf).

**Grading:** Midterm 25% · Paper 25% · Final 40% · Section participation 10%

**Companion book:** Hayes later turned these lectures into a book,
[*Introduction to the Bible*](https://yalebooks.yale.edu/book/9780300181791/introduction-to-the-bible/)
(Yale University Press), which is a useful single-volume companion.

## My progress

Click the ✏️ edit button on GitHub and change `[ ]` to `[x]` as you finish each one.

{progress}

---

<sub>{LICENSE} Readings are linked, not copied. Bible text links go to Sefaria and BibleGateway, and books link
to the Internet Archive lending library.</sub>
"""
write(os.path.join(CDIR, 'README.md'), readme)

top = f"""# 📜 History

My personal study space for history. Each course gets its own folder with every lecture, reading, transcript and
handout linked in one place, so there's nothing to hunt down.

## Courses

| Course | Source | Lectures | Start here |
|---|---|---|---|
| **Introduction to the Old Testament (Hebrew Bible)** | Yale RLST 145 · Prof. Christine Hayes | 24 | [Open course →]({SLUG}/README.md) |

## Folder layout

```
History/
└── {SLUG}/
    ├── README.md        ← course home: lecture list, textbooks, syllabus, progress checklist
    ├── lectures/        ← one page per lecture: video, audio, readings with links, full transcript
    └── handouts/        ← every handout and exam PDF from the course
```
"""
write(os.path.join(OUT, 'README.md'), top)

# ---------------------------------------------------------------- report
for L in lectures:
    print(f"L{L['n']:>2} ch={len(L['chapters'])} words={len(L['transcript'].split()):>6} "
          f"overview={len(L['overview']):>4} res={len(L['resources'])} srcs={sum(bool(re.search(p, L['assign_text'])) for p, _ in SOURCES)} | {L['title']}")
