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
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'}
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
# Every reading gets a free, legal source. 'open' = free online, no account; 'borrow' = free Internet Archive
# loan (free account); 'partial' = part of it is free online; 'library' = only via a public library card.
IA = 'https://archive.org/details/'
LIBRARY = 'free with a public library card (as an e-book through Libby or Hoopla if your library has it, otherwise by Interlibrary Loan)'
JSTOR_NOTE = 'readable online with a free [JSTOR personal account](https://www.jstor.org/register)'


def ia_page(ident, n):
    return f'{IA}{ident}/page/{n}/mode/2up'


def find_in(ident, q):
    return f'{IA}{ident}?q=' + urllib.parse.quote_plus(q)


def alive(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def R(pat, title, status, links, note=''):
    return dict(pat=pat, title=title, status=status, links=links, note=note)


JSB = 'jewishstudybible0000unse_x6n0'
OTHER_READINGS = [
    R(r'Deluge|Creation Epic|Gilgamesh', 'Pritchard, ed., *The Ancient Near East*, Vol. 1: "The Deluge," "The Creation Epic," '
      '"The Epic of Gilgamesh" (pp. 28–75)', 'borrow',
      [('Borrow Pritchard, opens at p. 28', ia_page('ancientneareasta00prit', 28)),
       ('free: Sumerian Flood Story (Oxford ETCSL)', 'https://etcsl.orinst.ox.ac.uk/section1/tr174.htm'),
       ('free: *Enuma Elish* (L. W. King, 1902)', 'https://sacred-texts.com/ane/enuma.htm'),
       ('free: *Gilgamesh* (R. Campbell Thompson, 1928)', 'https://sacred-texts.com/ane/eog/index.htm'),
       ('free: *Gilgamesh* (Jastrow & Clay, 1920)', 'https://www.gutenberg.org/ebooks/11000')],
      'The free versions are older translations of the same texts.'),
    R(r'Kaufmann', 'Kaufmann, *The Religion of Israel* (Schocken, 1972), pp. 21–121', 'borrow',
      [('Borrow, opens at p. 21', ia_page('religionofisrael0000kauf_j7j0', 21))]),
    R(r'Habel', 'Habel, *Literary Criticism of the Old Testament* (Fortress, 1971), pp. 1–42', 'library', [],
      'No free online copy exists (the Internet Archive copy is for print-disabled readers only).'),
    R(r'Boyarin', 'Boyarin, "Behold Israel According to the Flesh" and "Different Eves," in *Carnal Israel* (1993), '
      'pp. 31–46, 77–106', 'library', [],
      "UC Press's free e-book collection has this title, but for University of California users only."),
    R(r'Pagels', 'Pagels, *Adam, Eve, and the Serpent* (1988), pp. 57–77', 'library', []),
    R(r'Trible', 'Trible, "Depatriarchalizing in Biblical Interpretation," *JAAR* 41 (1973), pp. 30–48', 'borrow',
      [('Borrow the reprint in Koltun, *The Jewish Woman* (1976), pp. 217–240', ia_page('jewishwomannewpe0000kolt', 217)),
       ('or the original *JAAR* 41, p. 30', ia_page('journalofamerica0041unse', 30))]),
    R(r'Lot.s Wife', 'Goldstein, "Looking Back at Lot\'s Wife," in *Out of the Garden* (1994), pp. 3–12 (optional)',
      'open', [('Read free: first published in *Commentary*, Sept. 1992',
                'https://www.commentary.org/articles/rebecca-goldstein/looking-back-at-lots-wife/')]),
    R(r'Auerbach', 'Auerbach, "Odysseus\' Scar," *Mimesis*, ch. 1', 'borrow',
      [('Borrow *Mimesis* (Princeton, 1953), opens at ch. 1', ia_page('bwb_P9-ARY-273', 3)),
       ('or the reprint in *Homer: A Collection of Critical Essays* (1962), p. 19', ia_page('homercollectiono0000stei', 19))]),
    R(r'Alter, Robert', 'Alter, *The Art of Biblical Narrative* (1981), pp. 3–22, 47–62, 178–189', 'partial',
      [('pp. 3–22 free: first published as "A Literary Approach to the Bible," *Commentary*, Dec. 1975',
        'https://www.commentary.org/articles/robert-alter-2/a-literary-approach-to-the-bible/'),
       ('pp. 47–62 first published as "Biblical Type-Scenes and the Uses of Convention," *Critical Inquiry* 5.2 (1978)',
        'https://doi.org/10.1086/447994')],
      f'The *Critical Inquiry* article is {JSTOR_NOTE}. pp. 178–189 (the conclusion) are in the book only: {LIBRARY}.'),
    R(r'Greenstein', 'Preminger & Greenstein, eds., *The Hebrew Bible in Literary Criticism* (1986), "The Binding of '
      'Isaac," pp. 261–270', 'library', []),
    R(r'Milgrom', 'Milgrom, "Israel\'s Sanctuary: The Priestly \'Picture of Dorian Gray\'" (*Revue Biblique* 83, 1976)',
      'borrow',
      [('Borrow the reprint in Milgrom, *Studies in Cultic Theology and Terminology* (1983), pp. 75–84',
        ia_page('bwb_S0-BYL-636', 75)),
       ('or the same idea in his commentary, *Leviticus 1–16* (1991), p. 260', ia_page('leviticus11600jaco', 260))]),
    R(r'Eshnunna', 'Pritchard, ed., *The Ancient Near East*, Vol. 1: "The Laws of Eshnunna," "The Code of Hammurabi" '
      '(pp. 133–166)', 'borrow',
      [('Borrow Pritchard, opens at p. 133', ia_page('ancientneareasta00prit', 133)),
       ('free: *Code of Hammurabi* (L. W. King, Yale Avalon Project)', 'https://avalon.law.yale.edu/ancient/hamframe.asp')]),
    R(r'Ancient Near Eastern Texts Relating', 'Pritchard, ed., *ANET*, "Collections of Laws from Mesopotamia": Sumerian '
      'Laws, Ur-Nammu, Lipit-Ishtar, Middle Assyrian Laws, Hittite Laws (consult)', 'borrow',
      [('Borrow Schreiber, *Jewish Law and Decision-Making* (1979), which reprints the ANET translations: '
        'Ur-Nammu p. 83', ia_page('jewishlawdecisio0000schr', 83)),
       ('Lipit-Ishtar p. 85', ia_page('jewishlawdecisio0000schr', 85)),
       ('Middle Assyrian Laws p. 91', ia_page('jewishlawdecisio0000schr', 91)),
       ('Hittite Laws p. 95', ia_page('jewishlawdecisio0000schr', 95)),
       ('Sumerian Laws: borrow Pritchard, *The Ancient Near East*, Vol. 2 (1975)',
        find_in('ancientneareastv0000unse', '"Sumerian Laws"'))]),
    R(r'Interpretation, History of', '*Anchor Bible Dictionary*, "Interpretation, History of," pp. 424–427, 434–436',
      'borrow', [('Borrow vol. 3, opens at p. 424', ia_page('anchorbibledicti0003unse_b2a9', 424))]),
    R(r'Reis', 'Reis, "Spoiled Child: A Fresh Look at Jephthah\'s Daughter," in *Reading the Lines* (2002) (optional)',
      'borrow', [('Borrow, opens at the essay', find_in('readinglinesfres0000reis', '"Spoiled Child"'))]),
    R(r'Sternberg', 'Sternberg, *The Poetics of Biblical Narrative* (1985), pp. 186–222', 'partial',
      [('Same analysis (David and Bathsheba) as an article: Perry & Sternberg, "The King through Ironic Eyes," '
        '*Poetics Today* 7.2 (1986)', 'https://www.jstor.org/stable/1772762')],
      f'The article is {JSTOR_NOTE}. The book itself: {LIBRARY}.'),
    R(r'Psychopathology', 'Levinson, "The Psychopathology of King Saul," in *Out of the Garden*, pp. 123–141 (optional)',
      'library', []),
    R(r'Hannah and Elkanah', 'Ozick, "Hannah and Elkanah: Torah as the Matrix for Feminism," in *Out of the Garden*, '
      'pp. 88–93 (optional)', 'partial',
      [('free excerpt of the first version, *Lilith* 12/13 (1985)',
        'https://lilith.org/articles/from-torah-as-the-matrix-for-feminism/')], f'Full essay: {LIBRARY}.'),
    R(r'Encyclopedia of Religion', 'Wilson, "Biblical Prophecy," *The Encyclopedia of Religion* 12:14–23', 'borrow',
      [('Borrow vol. 12, opens at p. 14', ia_page('encyclopediaofre12elia', 14))]),
    R(r'Apocalypses', '*Anchor Bible Dictionary*, "Apocalypses," pp. 279–288', 'borrow',
      [('Borrow vol. 1, opens at p. 279', ia_page('anchorbibledicti0001unse_l6c5', 279))]),
]

_urls = sorted({u for r in OTHER_READINGS for _, u in r['links'] if 'archive.org' not in u and 'jstor.org' not in u
                and 'doi.org' not in u})
with cf.ThreadPoolExecutor(8) as ex:
    ok = dict(zip(_urls, ex.map(alive, _urls)))
print('free-text links alive:', ok)


def links_md(r):
    return ' · '.join(f'[{label}]({u})' for label, u in r['links'] if ok.get(u, True))


def reading_line(r):
    out = f"**{r['title']}** → " + (links_md(r) or LIBRARY[0].upper() + LIBRARY[1:])
    return out + (f". {r['note']}" if r['note'] else '')


JSB_CITE = re.compile(r'(Introduction to [A-Za-z][^(\n;]*?|"[^"]+"|“[^”]+”)\s*[,(]\s*(?:JSB\s*)?pp\.?\s*([\d][\d\s,\-–]*(?:and\s*[\d\-–\s,]+)?)')


def jsb_line(text):
    """Deep-link every 'Introduction to X (JSB pp. a-b)' citation to its page in the borrowable JSB."""
    seen, parts = set(), []
    for label, pages in JSB_CITE.findall(text):
        label = label.strip(' ,').strip('"“”')
        ranges = re.findall(r'(\d+)(?:\s*[-–]\s*(\d+))?', pages)
        # "Introduction to Lamentations, Proverbs, Job and Ecclesiastes (pp. a, b, c, d)": one label per range
        names = re.split(r',\s*|\s+and\s+(?:Introduction to\s+)?', label[len('Introduction to '):])
        labels = ([f'Introduction to {x}' for x in names] if label.startswith('Introduction to ')
                  and len(names) == len(ranges) > 1 else [label] * len(ranges))
        for label, (a, b) in zip(labels, ranges):
            key = (label, a)
            if key in seen:
                continue
            seen.add(key)
            parts.append(f"[{label}, pp. {a}{'–' + b if b else ''}]({ia_page(JSB, a)})")
    if not parts:
        return ''
    return ('**The Jewish Study Bible** (the course textbook, Oxford 2004) → [borrow free]({}) (free Internet Archive '
            'account). Each link opens at the assigned page: ').format(IA + JSB) + ' · '.join(parts)


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
    found = [jsb_line(L['assign_text'])] + [reading_line(r) for r in OTHER_READINGS if re.search(r['pat'], L['assign_text'])]
    where = '\n'.join(f'- {t}' for t in found if t) or '- _Everything for this lecture is in the Bible table above._'
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

# ---------------------------------------------------------------- free readings page
for r in OTHER_READINGS:
    r['lectures'] = [L for L in lectures if re.search(r['pat'], L['assign_text'])]
groups = [('open', '🆓 Free online, no account needed'),
          ('borrow', '📖 Free to borrow on the Internet Archive'),
          ('partial', '🆓 Partly free online'),
          ('library', '🏛️ Public library only')]
def lecture_links(r):
    return ', '.join(f"[{L['n']}](lectures/{L['file']})" for L in r['lectures'])


sections = []
for status, heading in groups:
    rows = [f"| {r['title']} | {lecture_links(r)} | {reading_line(r).split(' → ', 1)[1]} |"
            for r in OTHER_READINGS if r['status'] == status and r['lectures']]
    if rows:
        sections.append(f'## {heading}\n\n| Reading | Lectures | Where to read it free |\n|---|---|---|\n' + '\n'.join(rows))
counts = {s: sum(1 for r in OTHER_READINGS if r['status'] == s and r['lectures']) for s, _ in groups}
free_md = f"""# Free readings

[← Course home](README.md)

Every non-Bible reading in the course, with a free and legal way to read it. Nothing here needs to be bought.
(The Bible passages are on each lecture page, linked to Sefaria and BibleGateway.)

**How the links work**

- **Internet Archive "Borrow" links:** make a free account at [archive.org](https://archive.org/account/signup), then
  click **Borrow** (a 1-hour loan you can renew, or 14 days for some books). Page links open at the assigned page; if
  one lands elsewhere, type the page number into the reader's page box.
- **Public library:** a free library card gets you e-books through Libby or Hoopla, and anything else through
  Interlibrary Loan. Most of the library-only readings are optional or for section discussion.
- **JSTOR articles:** a free [JSTOR personal account](https://www.jstor.org/register) lets you read a limited number
  of articles online each month.

**Tally:** {counts['open']} free online · {counts['borrow']} free to borrow · {counts['partial']} partly free online · {counts['library']} library only

## 📗 The textbook: *The Jewish Study Bible* (Oxford, 2004)

Used in almost every lecture. [Borrow it free]({IA}{JSB}) (the same 2004 edition the course used). Each lecture
page links every assigned *JSB* section straight to its page.

{chr(10).join(s + chr(10) for s in sections)}
**Not linked on purpose:** uploads of these copyrighted books on "folkscanomy," "pdfdrive" or similar
collections are unauthorized copies, so they are left out.
"""
write(os.path.join(CDIR, 'free-readings.md'), free_md)

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
# keep the checkmarks already ticked in the existing README, so a rebuild never loses progress
try:
    with open(os.path.join(CDIR, 'README.md'), encoding='utf-8') as f:
        old_readme = f.read()
except FileNotFoundError:
    old_readme = ''
done = {int(n) for n in re.findall(r'(?m)^- \[x\] \[Lecture (\d+):', old_readme, re.I)}
midterm_done = bool(re.search(r'(?m)^- \[x\] Midterm', old_readme, re.I))
progress = '\n'.join(f"- [{'x' if L['n'] in done else ' '}] [Lecture {L['n']}: {L['title']}](lectures/{L['file']})"
                     + (f"\n- [{'x' if midterm_done else ' '}] Midterm: try the [exam](handouts/midterm-exam.pdf) using the "
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
   a free link for every other reading (see [Free readings](free-readings.md) for the full list).
3. **Watch the lecture** (YouTube) or **listen** (MP3). Use the chapter timestamps to jump around.
4. **Review with the transcript**, which is on the same page below the readings.

## Lectures

| # | Lecture (readings + transcript) | Bible reading | Watch | Listen |
|---|---|---|---|---|
{chr(10).join(rows)}

## Textbooks & readings

**📚 [Free readings](free-readings.md): every non-Bible reading in the course, with a free, legal way to read it.**

The two main books can be borrowed free from the Internet Archive (you need a free account):

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
    ├── free-readings.md ← every non-Bible reading with a free, legal link
    ├── lectures/        ← one page per lecture: video, audio, readings with links, full transcript
    └── handouts/        ← every handout and exam PDF from the course
```
"""
write(os.path.join(OUT, 'README.md'), top)

# ---------------------------------------------------------------- report
for L in lectures:
    print(f"L{L['n']:>2} ch={len(L['chapters'])} words={len(L['transcript'].split()):>6} "
          f"overview={len(L['overview']):>4} res={len(L['resources'])} srcs={sum(bool(re.search(r['pat'], L['assign_text'])) for r in OTHER_READINGS)} | {L['title']}")
