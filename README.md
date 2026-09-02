# instructions

1. copy `course_rules.yaml.example` to `course_rules.yaml` and edit it to suit your needs
2. run `main.py`
3. ...
4. profit

Output is created only when there's a match, so running it with cron and email set up should work fine.

## the 500-row cap

The openings page truncates its table at 500 rows and gives no sign that it did — a plain
request looks like a complete catalog but isn't. The real total is currently ~750.

`get_all_courses()` works around this by querying one class-name prefix at a time via the
page's `cname` parameter (`Baby`, `Toddler`, `Level 1`…`Level 5`, `Adult`), each of which
comes in well under the cap, and merging the results. If any single query ever comes back
with exactly 500 rows it warns on stderr, which means a prefix has outgrown the cap and needs
splitting further.

Worth knowing when filtering:

- **Only classes with open seats are listed.** No result means "no availability", not "no
  such class".
- **Class names are hand-typed and inconsistently spaced** — `ages 3-5` and `ages 3 -5` both
  occur, so a literal `name_includes` token can silently drop classes.
- **`instructors` cannot be empty**, since `any([])` is `False` and an absent list matches
  nothing. To mean "any instructor", list substrings that catch everything (the vowels work).
