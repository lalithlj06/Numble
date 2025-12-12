from typing import List

def validate_secret(number: str) -> bool:
    if not number.isdigit() or len(number) != 4:
        return False
    # Check for repeating digits
    if len(set(number)) != 4:
        return False
    return True

def validate_guess(guess: str, secret: str) -> List[str]:
    # Returns a list of 4 colors: "green", "yellow", "grey"
    result = ["grey"] * 4
    secret_list = list(secret)
    guess_list = list(guess)
    
    # First pass: find greens (correct pos)
    for i in range(4):
        if guess_list[i] == secret_list[i]:
            result[i] = "green"
            secret_list[i] = None # Mark as used
            guess_list[i] = None
            
    # Second pass: find yellows (wrong pos)
    for i in range(4):
        if guess_list[i] is None:
            continue
            
        if guess_list[i] in secret_list:
            result[i] = "yellow"
            # Remove FIRST occurrence of this digit from secret_list to handle duplicates correctly?
            # Wait, duplicates aren't allowed in secret number per rules.
            # "Digits cannot repeat" -> Simplifies logic massively.
            # But standard Wordle logic usually handles it.
            # Since duplicates are BANNED, we don't need to worry about complex double-letter logic.
            
    return result
