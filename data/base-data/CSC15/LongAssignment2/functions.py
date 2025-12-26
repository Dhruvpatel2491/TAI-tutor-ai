"""
functions.py

This file contains only function signatures, detailed docstrings and step-by-step pseudocode.
You must implement the bodies according to the descriptions.

All functions should:
 - normalize alphabetic characters to uppercase for processing (but preserve non-letters as specified),
 - Leave non-alphabetic characters (spaces, punctuation, digits) unchanged unless stated.
 - Keep encrypt/decrypt pairs consistent.

Each function here raises NotImplementedError to indicate it must be implemented by you.
"""

# Frequency distribution of letters in English text (percentage)
ENGLISH_FREQ = {
    'A': 8.17, 'B': 1.49, 'C': 2.78, 'D': 4.25, 'E': 12.70,
    'F': 2.23, 'G': 2.02, 'H': 6.09, 'I': 6.97, 'J': 0.15,
    'K': 0.77, 'L': 4.03, 'M': 2.41, 'N': 6.75, 'O': 7.51,
    'P': 1.93, 'Q': 0.10, 'R': 5.99, 'S': 6.33, 'T': 9.06,
    'U': 2.76, 'V': 0.98, 'W': 2.36, 'X': 0.15, 'Y': 1.97, 'Z': 0.07
}


# --- Helpful notes for students (not executable) ---
#
# Conventions to follow in your implementations:
#  - When the docstring says "letters uppercased", you should convert alphabetic chars to uppercase
#    for the cipher operations. You may keep non-alpha characters (spaces, punctuation) in place,
#    except where the pseudocode explicitly says to strip them.
#  - Use 'A'..'Z' mapping (26 letters) for shifts.
#  - Keep behavior consistent across encrypt/decrypt (docstrings explain expected inputs/outputs).
#  - Provide helpful error messages for invalid arguments (e.g., empty keyword, num_cols < 2).
#
# For the transposition cipher we require a KEYWORD variant:
#  - If the user provides an integer N, behave as classic column count = N.
#  - If the user provides a string keyword (e.g., "SECRET"), compute column order by
#    sorting letters of the keyword (ties broken by left-to-right index).
#    E.g., keyword "ZEBRA" -> letters with indices [Z,E,B,R,A]
#    sorted order A(4), B(2), E(1), R(3), Z(0) -> column order [4,2,1,3,0].
#  - The encrypt/decrypt docstrings below describe this in more detail.

# ----------------- Caesar -----------------
def caesar_encrypt(plaintext: str, shift: int) -> str:
    """
    Encrypt plaintext using the Caesar cipher.

    Args:
        plaintext: input string. Letters will be uppercased for the cipher; non-letters are left unchanged.
        shift: integer number of positions to shift (may be negative or larger than 26).

    Returns:
        ciphertext: string where each alphabetic character has been shifted by 'shift' positions (A..Z),
                    letters are uppercase in the result; non-letter characters unchanged.

    PSEUDOCODE / Implementation hints:
      0. output = "" (empty list to collect characters)
      1. for each character c in plaintext:
           - If c is alphabetic: 
             convert to uppercase
             compute index = ord(c) - ord('A')
             new_index = (index + (shift mod 26)) mod 26
             append chr(new_index + ord('A')) to output
           - Else: append c unchanged
      2. Return joined output string.

    Precondition (need to check with an if statement and raise an error):
        ValueError if plaintext is None.
        TypeError if shift is not an integer.
        ValueError if shift is not between 0 and 25 (inclusive).
    """
    if plaintext is None:
        raise ValueError("plaintext cannot be None")
    if not isinstance(shift, int): # if shift is not an integer
        raise TypeError("shift must be an integer")
    # raise a ValueError if shift is not between 0 and 25 (inclusive)

    raise NotImplementedError("Implement caesar_encrypt according to the pseudocode and comment this exception")


def caesar_decrypt(ciphertext: str, shift: int) -> str:
    """
    Decrypt ciphertext using the Caesar cipher with the given shift.

    Args:
        ciphertext: encrypted string produced by caesar_encrypt.
        shift: the integer shift that was used to encrypt (same semantics as caesar_encrypt).

    Returns:
        plaintext: decrypted string (letters uppercase; non-letters unchanged).

    PSEUDOCODE:
      - Decryption is the inverse operation: call the same shifting with -shift,
        or for each letter do inverse shift: new_index = (index - (shift mod 26)) mod 26.

    Preconditions:
        ValueError if cyphertext is None.
        TypeError if shift is not an integer.
        ValueError if shift is not between 0 and 25 (inclusive).
    """
    # add precondition checks as in caesar_encrypt

    raise NotImplementedError("Implement caesar_decrypt according to the docstring pseudocode and comment this exception")


# ----------------- Vigenère -----------------
def vigenere_encrypt(plaintext: str, keyword: str) -> str:
    """
    Encrypt plaintext using the Vigenère cipher.

    Args:
        plaintext: input string. Non-letters remain unchanged; letters are uppercased for processing.
        keyword: alphabetic keyword; e.g., "LEMON". Must contain at least one alphabetic character. 
                                Raises ValueError if invalid.
    Returns:
        ciphertext: encrypted string (letters uppercase; non-letters unchanged).

    PSEUDOCODE / Implementation hints:
      1. Validate keyword: remove non-alpha chars from keyword; if resulting keyword is empty -> raise ValueError.
      2. Upper case all letters in the keyword -> keyword_upper
      3. Convert keyword_upper to a list of shifts: for each letter k in keyword_upper the shift value is ord(k)-ord('A'). 
      Store all shifts in a list keyword_shifts.
        For example, keyword "LEMON" -> keyword_shifts [11,4,12,14,13]
        L = 11 (L is 11 positions from A)
        E  = 4  (E is 4 positions from A)  
        M = 12 (M is 12 positions from A)
        O = 14 (O is 14 positions from A)
        N = 13 (N is 13 positions from A)
      4. output = "" (empty string to collect characters)
      3. Iterate through plaintext characters with an index key_pos initially 0 (use a while loop)
           - For each character c in plaintext:
               * If c is a letter:
                   - compute shift = keyword_shifts[key_pos % len(keyword_shifts)]
                   - convert c to uppercase, compute index = ord(c)-ord('A')
                   - encrypted_char = chr(((index + shift) mod 26) + ord('A'))
                   - append encrypted_char to output; 
                   - increment key_pos
               * Else:
                   - append c unchanged to output (do not increment key_pos)
      4. Return output.

    Preconditions: 
        ValueError if plaintext is None.
        ValueError if keyword is None or empty after removing non-alpha characters.
    """

    # add additional precondition checks and raise errors if not satisfied
    # after removing non-alpha chars, keyword must not be empty
    if keyword is None:
        raise ValueError("keyword cannot be None")
    # convert to uppercase letters

    raise NotImplementedError("Implement vigenere_encrypt according to the docstring pseudocode")


def vigenere_decrypt(ciphertext: str, keyword: str) -> str:
    """
    Decrypt ciphertext produced by vigenere_encrypt.

    Args:
        ciphertext: encrypted string.
        keyword: the same keyword used for encryption.

    Returns:
        plaintext: decrypted string (letters uppercase; non-letters unchanged).

    PSEUDOCODE:
      - Similar to encrypt but apply shift = -keyword_shift when computing the decrypted letter.
      - Maintain key_pos alignment across alphabetic characters only.
    
    Preconditions:
        ValueError if ciphertext is None.
        ValueError if keyword is None or empty after removing non-alpha characters.  
         same as in the encrypt function.
    """

    # add additional precondition checks and raise errors if not satisfied
    # after removing non-alpha chars, keyword must not be empty
    if keyword is None:
        raise ValueError("keyword cannot be None")
    # convert to uppercase letters

    raise NotImplementedError("Implement vigenere_decrypt according to the docstring pseudocode")


# ----------------- Columnar Transposition (keyword-based) -----------------
def _compute_column_order_from_keyword(keyword: str) -> list:
    """
    Helper funtion (call this function in the transposition_encrypt and transposition_decrypt).

    Purpose:
      - Given a keyword string (e.g. "ZEBRA"), compute and return a list 'order' of column indices
        that defines the order in which columns are read during encryption and decryption.

    Example:
      keyword = "ZEBRA"
      dict_keyword = {'Z':0, 'E':1, 'B':2, 'R':3, 'A':4}
      sorted by dictionary by letters: {'A':4, 'B':2, 'E':1, 'R':3, 'Z':0}
      return order = [4, 2, 1, 3, 0] (the values in the dictionary)

    PSEUDOCODE:
      1. Validate: keyword must have at least one alpha char.
      2. Build a dictionary (dict_keyword) with key = an uppercase letter, and value = index of the 
      uppercase letter in the string keyword. - use a for loop 
      3. Sort pairs by letter first, then by index: use sorted() on dict_keyword.items().
         This gives you list of tuples (letter, index) sorted by letter alphabetically.
      4. Extract all indices from the sorted list of tuples and store the in  a list called order. 
        Use a for loop
      5. Return that list of indices.

    Preconditions:
        ValueError if keyword is None.
    """
    # add precondition check for keyword None
    raise NotImplementedError("Implement _compute_column_order_from_keyword as a helper")


def transposition_encrypt(plaintext: str, key: int | str, pad_char: str = "X") -> str:
    """
    Encrypt using a columnar transposition cipher with either a numeric column count or a keyword.

    Args:
        plaintext: input string. Letters will be uppercased; non-letters remain in place.
        key: either an integer number of columns (>=2) or a keyword string used to compute column read order.
        pad_char: single character used to pad the final row if grid is incomplete (default 'X').

    Returns:
        ciphertext: string read column-wise according to the column order derived from key.

    PSEUDOCODE:
      1. Upper case the plaintext and keep non-letters in place.
      2. Determine number of columns:
           - If key is int: num_cols = int(key). Validate num_cols >= 2.
           - If key is str (keyword):
               * compute num_cols = length of keyword (after optionally removing non-alpha; document decision)
               * compute column_order = _compute_column_order_from_keyword(keyword)
      3. Fill grid row-wise: (use for loops)
           - Create rows as lists/strings by slicing plaintext into chunks of length num_cols.
           - If final chunk shorter than num_cols, pad with pad_char until its length == num_cols.
      4. Read columns in the order specified:
           - If key was int: read columns left-to-right (0..num_cols-1), within each column read top-to-bottom.
           - If key was keyword: read columns in the column_order computed in step 2.
      5. Concatenate and return ciphertext.

    Example (integer key):  
        Plaintext:  MEET AT 9PM!
        Key (cols): 4
        | M | E | E | T |
        | A | T |   | 9 |
        | P | M | ! | X |
    
       Encoded string: "MAPE TTM 9E !X"

    Example (string key):
      plaintext: Plaintext:  MEET AT 9 PM!
      Key:    ZEBRA, 
        Alphabetical order of keyword letters is A, B, E, R, Z,
        so we read columns in this order: [A, B, E, R, Z] = [4, 2, 1, 3, 0] 
        num_cols = 5, column_order = [4,2,1,3,0]
        | M | E | E | T |   |
        | A | T |   | 9 |   |
        | P | M | ! | X | X |  
        read in column order [4,2,1,3,0]:
        Encoded string: "  XE !ETMT9XMAP"

        Fill rows with length 5; pad final row; then read column 4 top-to-bottom, then 2, then 1, ...

    Preconditions:
        ValueError if plaintext is None.
        ValueError if key is an integer < 2.
        ValueError if key is a string and contains no alphabetic characters.
    """
    # add precondition checks for plaintext None, key validity
    raise NotImplementedError("Implement transposition_encrypt according to the docstring pseudocode")


def transposition_decrypt(ciphertext: str, key: int | str, pad_char: str = "X") -> str:
    """
    Decrypt columnar transposition ciphertext when given the key (int num_cols or keyword string).

    Args:
        ciphertext: string produced by transposition_encrypt.
        key: either integer columns or keyword string (same form used for encryption).
        pad_char: the pad character used during encryption (default 'X').

    Returns:
        plaintext: decrypted string. It may include padding characters at the end; or spaces at the beggining.

    PSEUDOCODE:
      1. Determine num_cols and column_order as in encrypt.
      2. Compute number of rows:
           rows = ceil(len(ciphertext) / num_cols)
      3. Compute length of each column - every column has length 'rows'. 
         All rows are full because of padding during encryption.       
    
      4. Slice the ciphertext into column strings in the read order used during encryption 
        (either 0,1, to num_cols-1) if key is an int or column_order if key is a keyword:
         
      5. Reconstruct rows by taking the i-th character of each column in original column index order for i in 0..rows-1.
      6. Concatenate rows into plaintext and return (optionally strip trailing pad_char if desired).

    Preconditions:
        ValueError if ciphertext is None.
        ValueError if key is an integer < 2.
        ValueError if key is a string and contains no alphabetic characters.
    """
    # add precondition checks for ciphertext None, key validity
    raise NotImplementedError("Implement transposition_decrypt according to the docstring pseudocode")


# ----------------- Extra credit: frequency-analysis decoders -----------------
def decode_caesar_frequency(ciphertext: str) -> (int, str):
    """
    Extra credit: attempt to decode a Caesar ciphertext using frequency analysis.

    Args:
        ciphertext: encrypted string (letters uppercase or mixed; function should normalize internally).

    Returns:
        (best_shift, plaintext_guess): integer shift that gave the best English-fit score and the plaintext string.

    PSEUDOCODE / Strategy:
      1. Normalize ciphertext (uppercase letters; optionally remove non-letters or ignore them in frequency counts).
      2. For each candidate shift s in 0..25:
           - candidate_plain = caesar_decrypt(ciphertext, s)
           - compute a scoring metric for candidate_plain vs English frequency distribution:
               * recommended: chi-squared statistic:
                   - count letter frequencies in candidate_plain (letters only)
                   - expected counts = ENGLISH_FREQ_percentage * total_letters / 100
                   - chi_sq = sum((observed - expected)^2 / expected) over A..Z
               * lower chi_sq indicates a better match to English
           - Keep the shift with the lowest score.
      3. Return best_shift and corresponding plaintext.

    Notes:
      - This method works well for moderate-length English plaintexts (> ~20 letters).
    """
    raise NotImplementedError("Implement decode_caesar_frequency according to the docstring pseudocode")


def decode_vigenere_frequency(ciphertext: str, max_keylen: int = 8) -> (str, str):
    """
    Extra credit: attempt to decode a Vigenère ciphertext via frequency analysis.

    Args:
        ciphertext: encrypted string.
        max_keylen: maximum key length to try (small integer, default 8).

    Returns a tuple:
        (best_key, plaintext_guess): guessed keyword (as a string of uppercase letters) and the plaintext guess.

    PSEUDOCODE / Strategy (basic but effective for short keys):
      1. Normalize ciphertext (uppercase letters; keep non-letters or ignore them for grouping but keep positions for decryption).
      2. For key_length in 1..max_keylen:
           - Split ciphertext into 'key_length' groups: group i contains every letter at positions where
             the count of letters seen so far % key_length == i (skip non-letters when grouping).
           - For each group, solve it as a Caesar cipher using decode_caesar_frequency logic to find the shift
             that best matches English frequency. That shift is the key letter for this position.
           - Assemble candidate_key from those shifts (convert shift -> 'A'..'Z').
           - Decrypt entire ciphertext with candidate_key using vigenere_decrypt.
           - Score the decrypted plaintext using chi-squared or another language metric.
      3. Return the candidate_key with the best overall plaintext score and the corresponding plaintext.

    Notes:
      - This is a simple Kasiski/IC-free approach: it uses per-column frequency matching and a brute-force search
        over small key lengths. It is heuristic and may fail for very short ciphertexts or non-English plaintexts.
    """
    raise NotImplementedError("Implement decode_vigenere_frequency according to the docstring pseudocode")


def decode_transposition_frequency(ciphertext: str, max_cols: int = 10) -> (int | str, str):
    """
    Extra credit: attempt to decode a columnar transposition ciphertext by trying different column counts
    (or keyword lengths) and scoring the resulting plaintexts by English frequency.

    Args:
        ciphertext: encrypted string.
        max_cols: maximum number of columns (or keyword length) to try.

    Returns:
        (best_key_candidate, plaintext_guess): best guessed key (int for num_cols or string for keyword, if trying keywords)
                                               and the plaintext guess.

    PSEUDOCODE / Strategy:
      1. Normalize ciphertext.
      2. For each candidate number of columns c in 2..max_cols:
           - Attempt to transposition_decrypt(ciphertext, c) under the assumption encryption used padding.
             (If your encrypt used keyword ordering, you may try simple numeric columns first.)
           - Score the resulting plaintext using chi-squared or another English-likeness metric.
      3. Optionally: If you want to search keyword-based transpositions, you can:
           - Iterate over candidate keyword lengths L up to some small bound,
           - For each L, generate candidate keyword orders by heuristics (expensive if brute-forcing permutations).
             This is optional and not required for extra credit.
      4. Return the best candidate (column count or keyword) and plaintext with lowest score.

    Notes:
      - This is computationally heavier than the Caesar/Vigenère decoders. Keep max_cols small (e.g., <= 10).
      - For short ciphertexts the metric may not be reliable.
    """
    raise NotImplementedError("Implement decode_transposition_frequency according to the docstring pseudocode")
