# Tools

## estimate_length.py

Estimates how many typewritten pages a post would fill, and how long it takes to
read. It needs only Python 3.

```sh
python3 notebooks/tools/estimate_length.py _posts/*.md
python3 notebooks/tools/estimate_length.py _posts/*.md --single-spaced
python3 notebooks/tools/estimate_length.py --write
```

`--write` measures every post in `_posts/` and saves the rounded pages and
minutes to `_data/lengths.yml`. The post layout shows them under the date. Run
it after editing a post, before you commit. Nothing runs it for you.

### Pages

The tool types the post the way a manuscript was typed on a classical typewriter.

| Choice | Value | Source |
|---|---|---|
| Paper | US Letter, 8.5 × 11 in, the most common size in the US | [Letter (paper size)](https://en.wikipedia.org/wiki/Letter_(paper_size)); [ANSI A in ANSI/ASME Y14.1](https://www.papersizes.org/us-paper-sizes.htm) |
| Type | Pica: 10 characters per inch, 6 lines per inch | [Pitch (typewriter)](https://en.wikipedia.org/wiki/Pitch_(typewriter)) |
| Layout | Double-spaced, 1-inch margins, monospaced type | [SFWA, Manuscript Format](https://sfwa.org/2005/01/04/manuscript-format/) |

That gives 65 characters per line and 27 typed lines per page (54 single-spaced).
Paragraphs start with a half-inch indent, five characters. Code blocks are typed
line by line. Front matter, Liquid tags and images are left out.

### Reading time

Prose words divided by 238 words per minute, the mean adult silent-reading rate
for English non-fiction. Most adults read non-fiction at 175 to 300 words per
minute, which gives the range. Code blocks are not counted.

Source: Marc Brysbaert, ["How many words do we read per minute? A review and
meta-analysis of reading rate"](https://doi.org/10.1016/j.jml.2019.104047),
*Journal of Memory and Language* 109 (2019), from 190 studies and 18,573 readers.
