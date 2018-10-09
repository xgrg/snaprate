# snaprate

Make it easier to collect quality control scores from a panel of experts.

The tool works as a webpage where experts can review snapshots across subjects.
It is designed so that every subject may have a fixed number of snapshots
(e.g. corresponding to various segmentation methods).
The order of the snapshots is randomized per subject so that the rater is blind
to the segmentation method.
The raters may then input a sequence, for every subject, ranking each tuple of
snapshots by decreasing order of preference.

> Ex: inputting "213" for subject X would mean that snapshot #2 is the best one,
followed by snapshot #1, while snapshot #3 is the worst. Any input not respecting
this format would be rejected (in this current version).

Every ranking is stored server-side in an individual file per rater. It is saved
 automatically subject after subject. Any previously stored ranking will be
  displayed along with its corresponding subject.

Users should login on the system using individual login/password opening a
browser to the local network address where the server is running.

![screenshot.png](screenshot.png)

## Usage:

- **Server-side**:
  - place a collection of snapshots in `$PATH/web/images/`
  - rewrite the `collect_snapshots` function in `snaprate/snaprate.py` so as to
     return lists of paths to snapshots indexed by subject
  - run the web server (`python $PATH/python/snaprate/snaprate.py`)

- **Client-side**: open a browser pointing to the server address (and defined
  port (default:8890))

**Note:** this code was initially written to allow comparisons across different
methods over a group of subjects. In this context, inputs should follow a
certain format, as explained earlier and as implemented in `validate()`
(`web/html/index.html`).
Hence it may be adapted to various applications (even when snapshots come from
  one method only) e.g. by rewriting `validate()`.

## Dependencies:

- tornado
- pandas
