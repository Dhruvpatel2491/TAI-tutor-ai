# test.py
# Simple class-free tests for the ciphers assignment.
# Run with: python test.py
# Tests will raise AssertionError (and mark fail) if something is wrong.
# If functions are not implemented yet (raise NotImplementedError), that will be reported.

import traceback
from functions import (
    caesar_encrypt, caesar_decrypt,
    vigenere_encrypt, vigenere_decrypt,
    transposition_encrypt, transposition_decrypt,
    decode_caesar_frequency, decode_vigenere_frequency, decode_transposition_frequency
)

passed = 0
failed = 0

def run(name, fn):
    global passed, failed
    try:
        fn()
        print(f"[PASS] {name}")
        passed += 1
    except NotImplementedError:
        print(f"[FAIL] {name} — NotImplementedError (function not implemented yet)")
        failed += 1
    except AssertionError as e:
        print(f"[FAIL] {name} — AssertionError: {e}")
        failed += 1
    except Exception as e:
        print(f"[ERROR] {name} — unexpected exception:")
        traceback.print_exc()
        failed += 1

# ---------- Tests ----------

def test_caesar_basic():
    pt = "MEET AT NOON."
    ct = caesar_encrypt(pt, 3)
    assert isinstance(ct, str)
    assert ct == "PHHW DW QRRQ."  # expected from manual example
    dec = caesar_decrypt(ct, 3)
    assert dec == pt  # should recover original (uppercase rule already applied in functions)

def test_caesar_roundtrip_nonalpha():
    pt = "Meet at 9pm! Bring 2 bats."
    ct = caesar_encrypt(pt, 7)
    dec = caesar_decrypt(ct, 7)
    # letters should be recovered (uppercased) and digits/punct still present
    assert "MEET" in dec
    assert "9PM" in ct or "9pm" in ct  # cipher keeps non-letters unchanged

def test_vigenere_basic():
    pt = "ATTACK AT DAWN!"
    key = "LEMON"
    ct = vigenere_encrypt(pt, key)
    dec = vigenere_decrypt(ct, key)
    assert dec == pt  # functions expected to uppercase letters; compare to given plaintext

def test_vigenere_with_nonletters():
    pt = "THE QUICK, BROWN FOX."
    key = "KEY"
    ct = vigenere_encrypt(pt, key)
    dec = vigenere_decrypt(ct, key)
    assert dec == pt  # non-letters preserved and key alignment skips them

def test_transposition_numeric_columns():
    pt = "ATTACK AT DAWN"
    ct = transposition_encrypt(pt, 4)   # numeric key
    dec = transposition_decrypt(ct, 4)
    # decrypted may include trailing padding; ensure original appears at start
    assert dec.startswith(pt)

def test_transposition_keyword():
    pt = "MEET AT 9 PM!"
    key = "ZEBRA"
    ct = transposition_encrypt(pt, key)
    dec = transposition_decrypt(ct, key)
    # ensure decryption returns original text (padding may exist)
    assert dec.startswith(pt)

# Extra-credit decoder tests
def test_decode_caesar_frequency():
    pt = "MEET AT MIDNIGHT"
    ct = caesar_encrypt(pt, 5)
    result = decode_caesar_frequency(ct)
    assert isinstance(result, tuple) or isinstance(result, list)
    # expect two values (shift, plaintext)
    shift, guess = result
    # check that the returned plaintext matches applying the reported shift
    assert caesar_decrypt(ct, shift) == guess
    assert "MEET" in guess

def test_decode_vigenere_frequency():
    pt = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"
    key = "KEY"
    ct = vigenere_encrypt(pt, key)
    result = decode_vigenere_frequency(ct, max_keylen=6)
    assert isinstance(result, tuple) or isinstance(result, list)
    guessed_key, guess_plain = result
    # guessed_key may vary; check the plaintext guess looks English
    assert isinstance(guess_plain, str)
    assert "THE" in guess_plain or "QUICK" in guess_plain

def test_decode_transposition_frequency():
    pt = "ATTACK AT DAWN"
    ct = transposition_encrypt(pt, 4)
    result = decode_transposition_frequency(ct, max_cols=8)
    assert isinstance(result, tuple) or isinstance(result, list)
    guessed_key, guess_plain = result
    # guessed_key could be an int (num_cols) or string (keyword); plaintext should contain recognizable word
    assert isinstance(guess_plain, str)
    assert "ATTACK" in guess_plain

# ---------- Run all tests ----------
tests = [
    ("Caesar basic", test_caesar_basic),
    ("Caesar roundtrip non-alpha", test_caesar_roundtrip_nonalpha),
    ("Vigenere basic", test_vigenere_basic),
    ("Vigenere with nonletters", test_vigenere_with_nonletters),
    ("Transposition numeric columns", test_transposition_numeric_columns),
    ("Transposition keyword", test_transposition_keyword),
    ("Decode Caesar (freq)", test_decode_caesar_frequency),
    ("Decode Vigenere (freq)", test_decode_vigenere_frequency),
    ("Decode Transposition (freq)", test_decode_transposition_frequency),
]

for name, func in tests:
    run(name, func)

print("\n--- Summary ---")
print(f"Passed: {passed}")
print(f"Failed: {failed}")

if failed > 0:
    raise SystemExit(1)
else:
    print("All tests passed!")
