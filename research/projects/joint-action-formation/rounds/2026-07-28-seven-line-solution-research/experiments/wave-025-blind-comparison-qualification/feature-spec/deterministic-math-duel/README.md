# Wave025 deterministic-math duel V2

Status: **`CANDIDATE STUDY / NOT CANON / NO G / NO FORMAL 3200`**

This post-redteam study asks a bounded question: which deterministic-math
semantics are genuinely different before a future `DETERMINISTIC-MATH`
candidate is written? It does not adopt a model-input layout, inherit the
rejected C01 v0 mini-suite, run G, or read a formal population.

## Compared paths

**A — fixed binary64 fold.** Every input and declared arithmetic operation is
rounded RN-ties-even to binary64 in a frozen order. Count transforms use a
frozen 256-entry `log1p(min(count,255))` table, so runtime `libm` is absent. It is
cheap and reproducible only if operation order, every-operation rounding,
FMA/contraction prohibition and KAT bytes are part of the contract.

**B — exact then last-round.** Rational preprocessing and collision sums remain
exact; already-binary64 matrix terms are exact dyadics; squared norms are
accumulated exactly and rounded after an integer/rational sqrt oracle. It needs
digit, term, exponent and intermediate-size ceilings. It can express a
mathematical multiset sum, but this study does not decide that the future formal
object must use that semantic.

The study installs no package and uses no MPFR or Arb. The sqrt kernel is
correctly rounded by exact rational midpoint comparison. The `log1p` cross-check
uses Python `Decimal.ln` at 80, 160 and 240 decimal digits. The independent
redteam additionally rebuilt all 256 entries with `/usr/bin/bc -l` at 100 and
220 digits and found the same bits. Neither reference produced rigorous error
intervals, so the table remains **`CORROBORATED_NOT_PROVEN`**, not “proved
correctly rounded.”

## Scoped kernel results

The rational converter's principal KATs are:

| Case | Binary64 big-endian bits | Admission |
|---|---:|---|
| `1 + 2^-53`, midpoint to even lower | `3ff0000000000000` | finite |
| `1 + 3*2^-53`, midpoint to even upper | `3ff0000000000002` | finite |
| maximum finite | `7fefffffffffffff` | finite |
| below overflow midpoint | `7fefffffffffffff` | finite |
| overflow midpoint | `7ff0000000000000` | `NOT_QUALIFIED_NUMERIC_RANGE`; never emitted |
| minimum normal | `0010000000000000` | finite |
| largest subnormal | `000fffffffffffff` | finite |
| minimum subnormal | `0000000000000001` | finite |
| `2^-1075`, underflow midpoint to even | `0000000000000000` | canonical +0 |
| `3*2^-1076`, above underflow midpoint | `0000000000000001` | finite |
| signed zero or negative underflow to zero | `0000000000000000` | canonical +0 |

The independent redteam found 8,882/8,882 exact-neighbor converter checks and
3,436/3,436 exact-cell sqrt checks consistent. These are scoped positive kernel
results. They do not validate the admission/resource wrappers or unlock G.

The pinned count table SHA-256 is
`0c91fac4170e278ff4e35b9c9ae026f749ffc326b9c94cc021c322d0993801d5`:

| Saturated count | `log1p` binary64 bits |
|---:|---:|
| 0 | `0000000000000000` |
| 1 | `3fe62e42fefa39ef` |
| 255 | `40162e42fefa39ef` |

All entries match the Decimal references with zero precision-instability and
zero bit disagreement. The V2 loader has no internal digest default: its caller
must supply the expected SHA as an external controller/reviewer input rather
than trusting a result self-report. `None`, integer and bytes pins now return a
stable binding failure instead of leaking a regex `TypeError`. The loader
requires the exact 12,870 bytes, RFC JSON without `NaN`/`Infinity`, exact frozen
string metadata, canonical encoding, 256 indexed entries, finite nonnegative
16-digit lowercase hex, no duplicate JSON keys/counts and no extra members.
This supports a frozen runtime lookup; release proof and release adoption remain
open.

## Five divergence cases, not five mechanisms

The paths are not byte-equivalent on the adversarial suite:

| Case | A bits | B bits | Difference |
|---|---:|---:|---|
| signed values `2^53, 1, -2^53` | `0000000000000000` | `3ff0000000000000` | fixed fold loses exact `1` |
| same multiset ordered `2^53, -2^53, 1` | `3ff0000000000000` | `3ff0000000000000` | order control |
| `1` followed by 1,024 terms of `2^-60` | `3ff0000000000000` | `3ff0000000000004` | small terms vanish under A |
| norm of `1` plus five components `2^-27` | `3ff0000000000000` | `3ff0000000000001` | A loses small squares |
| normalize `(2^53+1 - 2^53)/1` | `0000000000000000` | `3ff0000000000000` | pre-round erases unit shift |

The `averaged_inverted_cdf` four-point example adds a one-ULP instance of the
same broad pre-round-versus-last-round axis. These are five recorded cases across
three broad axes, not five independent mechanisms. Formal-input reachability and
effect on prediction or real tasks are both **`UNKNOWN`**.

Quantile examples remain examples, not selection evidence:

| Method | Center | IQR | Target 30, A bits | Target 30, B bits |
|---|---:|---:|---:|---:|
| exact type-7 | 15 | 15 | `3ff595810624dd2f` | `3ff595810624dd2f` |
| exact `averaged_inverted_cdf` | 15 | 20 | `3ff03020c49ba5e4` | `3ff03020c49ba5e3` |
| no center/no scale, then common clip | — | — | `4020000000000000` | `4020000000000000` |

Calibration `[7,7,7,7]` still uses zero-IQR fallback scale `1`; holdout `8`
becomes `1.0` in both paths. Type-7, averaged inverted CDF, raw/no-centering and
the inherited `IQR/1.349` choice still require the same task ablation.

## V2 admission and operator closure

Mathematical kernels are now separated from total evaluators. Every rational
leaf is admitted independently before any sum, square or cancellation:
canonical numerator/denominator digits, a post-parser binary-exponent guard and
finite binary64 range must pass. Thus `[2^1024,-2^1024,1]` fails on leaf zero;
exact cancellation cannot launder an illegal leaf.

The executable lifecycle is:

1. require unique raw-UTF8 column identities in ascending order and admit every
   rational leaf;
2. A rounds each column add; B exact-adds under caps and rounds once;
3. standardize by the declared path's subtract/divide operations, clip to
   `[-8,8]`, output-round and canonicalize zero;
4. family normalization independently verifies each input is an exact finite
   binary64 rational with `abs(component)<=8`, then computes a bounded norm,
   emits canonical zeros for a zero family, or divides by the rounded norm and
   output-rounds every component;
5. admit count as exact unsigned-64, apply `min(count,255)`, use the pinned table
   and canonicalize zero.

Every total evaluator returns either finite bits or `NOT_QUALIFIED` with a
stable code, stage and provenance. Regressions cover:

- sum, square, norm and output overflow;
- negative sqrt, exact-zero scale and nonzero scale that rounds to zero;
- illegal-leaf exact cancellation;
- term, digit, exponent and exact-intermediate caps;
- column order, duplicate identity and invalid UTF8;
- missing/non-string external pins; JSON `NaN`/`Infinity/-Infinity`; metadata
  drift; negative/wrong-width/uppercase table bits; duplicate keys/counts; wrong
  index; extra members and external-binding mismatch;
- count 0/1/255/256 saturation, clip ordering, zero-family normalization and
  `+0` output.

The third narrow fix also turns the family handoff precondition into executable
admission: an unclipped `100` fails at `FAMILY_INPUT_CLIP_BOUND`, and a rational
`1/3` fails at `FAMILY_INPUT_BINARY64_EXACT`. Legal `+8`, `-8`, exact minimum
subnormal and zero remain deterministic study inputs. A and B can still produce
different valid subnormal-norm results; this does not select a formal path.

The executable caps are study guards, not formal limits: 4,864 canonical
numerator/denominator decimal digits, absolute post-parser rational binary
exponent 14,000, 4,096 terms/samples, 16,384 intermediate numerator/denominator
bits, and 16,384 table bytes. The upstream V2S decimal-lexeme exponent cap 4,096
remains mandatory but cannot be reconstructed from a post-parser rational.

Exact operation counts and peak rational bit sizes are recorded for executed
cases. Wall-clock, CPU, peak RSS, formal 3,200 cost and the formal reachable
term/digit distribution remain **`UNKNOWN`**.

## Decision after redteam

B is **not wholesale deletable**, because universal A/B byte equivalence has
real counterexamples. This does not prove the current B implementation is the
minimal or required solution. The minimal sufficient set is
**`UNKNOWN_NOT_CLAIMED`**. Fixed-width superaccumulators, binned sums and scaled
integer alternatives have not faced the same input, task and cost constraints.

Before canon, the research must establish formal reachability and task impact,
replace study caps with justified limits, choose estimator and fold semantics,
compare mature alternatives, and obtain two independent provider rebuilds plus
holdback agreement. The package remains not canon, no G and no 3,200.

## Rebuild and verify

From this directory:

```bash
python3 deterministic_math_duel.py --expected-table-sha256 0c91fac4170e278ff4e35b9c9ae026f749ffc326b9c94cc021c322d0993801d5 --check RESULTS.candidate.json
python3 -m unittest discover -s tests -v
```

`RESULTS.candidate.json` binds the exact study source, independent redteam and
frozen table bytes. Normal verification never invokes host `libm`; it consumes
the pinned table and compares every entry with the documented Decimal reference.
