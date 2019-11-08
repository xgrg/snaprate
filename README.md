# snaprate

[![pipeline status](https://img.shields.io/travis/xgrg/snaprate.svg)](https://travis-ci.org/xgrg/snaprate)
[![pipeline status](https://coveralls.io/repos/github/xgrg/snaprate/badge.svg?branch=master)](https://coveralls.io/github/xgrg/snaprate?branch=master)

Make it easier to collect quality control scores from a panel of experts.

The tool works as a web application where experts can review snapshots across subjects.
Users may start a session on the system using individual login/password opening a
browser to the local network address where the server is running.

Once the server is running, users may log in using their
attributed credentials to start their review from the main screen:

![screenshot2.png](screenshot2.png)
![screenshot3.png](screenshot3.png)

- Buttons `previous subject`/`next subject` are used to navigate through the
different snapshots. As a result, the subject's identifier gets
 incremented/decremented. Any given ID may be accessed through direct URL:
 `<host>:<port>?id=<ID>` (ex: *localhost:8888?id=42*).

- Button `Your score` is for the user to quality current snapshot. Clicking on
it multiple times would turn it from not rated to green, then red, then orange,
then back to not rated. The text box located just under this button is for
potential comments. To save your review, just move on to the following/previous
subject.

- Each snapshot comes with an automatic prediction for quality, reflected by the
color (green or red) of the `Automatic prediction` button. The link located on
the left next to this button allows to skip to the next predicted failed case.
On the right is displayed information regarding volumes of gray and white
matter.

- User reviews are systematically and automatically stored server-side.
Nevertheless, button `download` allows to save them locally in an Excel table.


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

## Live action

![liveaction](demo.gif)
