# functions.py
# Implementations and docstrings for Caesar, Vigenere, and Columnar Transposition ciphers
# Plus simple frequency-analysis decoders (extra credit)

from typing import Tuple, Optional
import string
import math

ALPHABET = string.ascii_uppercase
ALPHA_LEN = len(ALPHABET)
ENGLISH_FREQ = {
    'A': 8.167, 'B': 1.492, 'C': 2.782, 'D': 4.253, 'E': 12.702, 'F': 2.228,
    'G': 2.015, 'H': 6.094, 'I': 6.966, 'J': 0.153, 'K': 0.772, 'L': 4.025,
    'M': 2.406, 'N': 6.749, 'O': 7.507, 'P': 1.929, 'Q': 0.095, 'R': 5.987,
    'S': 6.327, 'T': 9.056, 'U': 2.758, 'V': 0.978, 'W': 2.360, 'X': 0.150,
    'Y': 1.974, 'Z': 0.074
}

def _normalize_text(text: str) -> str:
    """Return uppercase text; leave non-alpha characters in place.
    Internal helper to unify behavior.
    """
    return ''.join(ch.upper() if ch.isalpha() else ch for ch in text)

def _shift_char(c: str, shift: int) -> str:
    if not c.isalpha():
        return c
    idx = ALPHABET.index(c.upper())
    return ALPHABET[(idx + shift) % ALPHA_LEN]

# ---------- Caesar Cipher ----------
def caesar_encrypt(plaintext: str, shift: int) -> str:
    """
    Encrypt plaintext using Caesar cipher.

    Args:
        plaintext: input string (letters, digits, punctuation allowed). Letters are shifted; case is normalized to uppercase.
        shift: integer number of positions to shift (can be negative or >26).

    Returns:
        ciphertext: encrypted string (letters uppercase; non-letters left unchanged).
    """
    pt = _normalize_text(plaintext)
    return ''.join(_shift_char(c, shift) for c in pt)

def caesar_decrypt(ciphertext: str, shift: int) -> str:
    """
    Decrypt ciphertext using Caesar cipher with given shift.

    Args:
        ciphertext: input encrypted string.
        shift: integer shift used during encryption.

    Returns:
        plaintext: decrypted string (uppercase letters; non-letters left unchanged).
    """
    return ''.join(_shift_char(c, -shift) for c in _normalize_text(ciphertext))

# ---------- Vigenere Cipher ----------
def _key_shifts_from_keyword(keyword: str):
    keyword = ''.join(ch.upper() for ch in keyword if ch.isalpha())
    if len(keyword) == 0:
        raise ValueError("Keyword must contain at least one alphabetic character")
    return [ALPHABET.index(ch) for ch in keyword]

def vigenere_encrypt(plaintext: str, keyword: str) -> str:
    """
    Encrypt plaintext using Vigenere cipher.

    Args:
        plaintext: input string. Non-letters left unchanged; letters uppercased.
        keyword: alphabetic keyword used to produce shifts (A=0, B=1, ...).

    Returns:
        ciphertext: encrypted string (uppercase letters; non-letters unchanged).
    """
    shifts = _key_shifts_from_keyword(keyword)
    pt = _normalize_text(plaintext)
    res = []
    k = 0
    for ch in pt:
        if ch.isalpha():
            shift = shifts[k % len(shifts)]
            res.append(_shift_char(ch, shift))
            k += 1
        else:
            res.append(ch)
    return ''.join(res)

def vigenere_decrypt(ciphertext: str, keyword: str) -> str:
    """
    Decrypt ciphertext using Vigenere cipher.

    Args:
        ciphertext: input encrypted string.
        keyword: keyword used for encryption.

    Returns:
        plaintext: decrypted string (uppercase letters; non-letters unchanged).
    """
    shifts = _key_shifts_from_keyword(keyword)
    ct = _normalize_text(ciphertext)
    res = []
    k = 0
    for ch in ct:
        if ch.isalpha():
            shift = shifts[k % len(shifts)]
            res.append(_shift_char(ch, -shift))
            k += 1
        else:
            res.append(ch)
    return ''.join(res)

# ---------- Columnar Transposition Cipher ----------
def transposition_encrypt(plaintext: str, num_cols: int) -> str:
    """
    Encrypt using a simple columnar transposition.

    Args:
        plaintext: input string. All characters are written row-wise (we keep non-letters too).
        num_cols: number of columns to use (>=2).

    Returns:
        ciphertext: read column-wise top-to-bottom, left-to-right.
    """
    if num_cols < 2:
        raise ValueError("num_cols must be >= 2")
    pt = _normalize_text(plaintext)
    # build rows
    rows = []
    for i in range(0, len(pt), num_cols):
        rows.append(pt[i:i+num_cols])
    # pad last row with filler (here we use X) so columns align
    last_len = len(rows[-1])
    if last_len < num_cols:
        rows[-1] = rows[-1] + 'X' * (num_cols - last_len)
    # read columns
    ciphertext = []
    for col in range(num_cols):
        for row in rows:
            ciphertext.append(row[col])
    return ''.join(ciphertext)

def transposition_decrypt(ciphertext: str, num_cols: int) -> str:
    """
    Decrypt a columnar transposition given number of columns.

    Args:
        ciphertext: input encrypted string.
        num_cols: number of columns used during encryption.

    Returns:
        plaintext: decrypted string (may include padding 'X' characters).
    """
    if num_cols < 2:
        raise ValueError("num_cols must be >= 2")
    ct = _normalize_text(ciphertext)
    n = len(ct)
    # number of full rows
    rows = math.ceil(n / num_cols)
    # number of full cells in first (n % rows) columns? For our simple encrypt we always padded to full matrix,
    # so we assume len(ct) == rows*num_cols
    if rows * num_cols != n:
        # if not padded, we still distribute: compute column lengths
        col_len = n // num_cols
        extra = n % num_cols
        cols = []
        idx = 0
        for c in range(num_cols):
            length = col_len + (1 if c < extra else 0)
            cols.append(ct[idx:idx+length])
            idx += length
    else:
        # balanced columns
        cols = []
        idx = 0
        for c in range(num_cols):
            cols.append(ct[idx:idx+rows])
            idx += rows
    # rebuild rows by taking i-th char from each column for each row
    plaintext_chars = []
    for r in range(rows):
        for c in range(num_cols):
            if r < len(cols[c]):
                plaintext_chars.append(cols[c][r])
    return ''.join(plaintext_chars)

# ---------- Extra credit: frequency-analysis decoders ----------
def _letter_frequencies(text: str) -> dict:
    counts = {ch:0 for ch in ALPHABET}
    total = 0
    for ch in text:
        if ch.isalpha():
            counts[ch] += 1
            total += 1
    if total == 0:
        return counts
    return {ch: (counts[ch] / total) * 100.0 for ch in ALPHABET}

def _chi_squared_score(text: str) -> float:
    # compute chi-squared statistic for text letter frequencies vs ENGLISH_FREQ
    obs = {ch:0 for ch in ALPHABET}
    total = 0
    for ch in text:
        if ch.isalpha():
            obs[ch] += 1
            total += 1
    if total == 0:
        return float('inf')
    score = 0.0
    for ch in ALPHABET:
        expected = ENGLISH_FREQ[ch] * total / 100.0
        observed = obs[ch]
        # avoid dividing by zero expected=0 extremely rare for english table
        if expected > 0:
            score += (observed - expected) ** 2 / expected
    return score

def decode_caesar_frequency(ciphertext: str) -> Tuple[int, str]:
    """
    Attempt to decode a Caesar ciphertext using frequency analysis.

    Args:
        ciphertext: encrypted text.

    Returns:
        (best_shift, plaintext_guess): shift (int) and resulting plaintext (uppercase).
    """
    ct = _normalize_text(ciphertext)
    best = None
    best_shift = 0
    for shift in range(0, ALPHA_LEN):
        candidate = caesar_decrypt(ct, shift)
        score = _chi_squared_score(candidate)
        if best is None or score < best:
            best = score
            best_shift = shift
            best_candidate = candidate
    return best_shift, best_candidate

def _split_by_key_length(text: str, key_len: int) -> list:
    """Return list of strings, each is the letters at positions i mod key_len."""
    groups = ['' for _ in range(key_len)]
    idx = 0
    for ch in text:
        if ch.isalpha():
            groups[idx % key_len] += ch
            idx += 1
        else:
            # skip non-alpha in key alignment
            pass
    return groups

def decode_vigenere_frequency(ciphertext: str, max_keylen: int = 8) -> Tuple[str, str]:
    """
    Attempt to decode Vigenere using frequency analysis (very basic).
    Strategy:
     - Try key lengths 1..max_keylen
     - For each key length, for each key-position, find Caesar shift that best matches English freq (chi-squared)
     - Build key and decrypt; score whole plaintext; pick best

    Args:
        ciphertext: encrypted string.
        max_keylen: maximum key length to try (default 8).

    Returns:
        (best_key, plaintext_guess)
    """
    ct = _normalize_text(ciphertext)
    best_score = None
    best_key = None
    best_plain = ''
    for keylen in range(1, max_keylen+1):
        groups = _split_by_key_length(ct, keylen)
        key_shifts = []
        for g in groups:
            # for this group find best Caesar shift
            best_local = None
            best_s = 0
            for s in range(ALPHA_LEN):
                cand = ''.join(_shift_char(ch, -s) for ch in g)
                score = _chi_squared_score(cand)
                if best_local is None or score < best_local:
                    best_local = score
                    best_s = s
            key_shifts.append(best_s)
        # convert shifts to keyword string
        key = ''.join(ALPHABET[s] for s in key_shifts)
        plain = vigenere_decrypt(ct, key)
        score = _chi_squared_score(plain)
        if best_score is None or score < best_score:
            best_score = score
            best_key = key
            best_plain = plain
    return best_key, best_plain

def decode_transposition_frequency(ciphertext: str, max_cols: int = 10) -> Tuple[int, str]:
    """
    Attempt to decode transposition by trying column counts up to max_cols and scoring the results.

    Args:
        ciphertext: encrypted string.
        max_cols: maximum number of columns to try.

    Returns:
        (best_num_cols, plaintext_guess)
    """
    ct = _normalize_text(ciphertext)
    best_score = None
    best_cols = None
    best_plain = ''
    for cols in range(2, min(max_cols, len(ct)) + 1):
        try:
            cand = transposition_decrypt(ct, cols)
        except Exception:
            continue
        score = _chi_squared_score(cand)
        if best_score is None or score < best_score:
            best_score = score
            best_cols = cols
            best_plain = cand
    return best_cols, best_plain
