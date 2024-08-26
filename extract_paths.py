import re
import os
import sys


def extract_paths(input_string):
    # Regular expression patterns for Unix-like and Windows paths
    unix_path_pattern = r"(\.{1,2}/\S+|/\S+|\b\S+/\S+\b)"  # Matches Unix-like paths, preserving leading "./", "../", and more dots
    windows_path_pattern = r"[a-zA-Z]:\\(?:[^\\\s,]+\\?)*[^\\\s,]+"  # Matches Windows paths, avoiding spaces and commas

    # Combine patterns to search for both types of paths
    combined_pattern = f"{unix_path_pattern}|{windows_path_pattern}"

    # Find all matches in the input string
    matches = re.findall(combined_pattern, input_string)

    print(matches)

    print([[isinstance(p, str)] for p in matches])

    if not all([[isinstance(p, str)] for p in matches]):
        print("[ WARNING ] Failed to extract paths in zsh_codex")
        return []

    return matches


if __name__ == "__main__":
    args = sys.argv
    input_string = args[1]

    extracted_paths = extract_paths(input_string)

    print(f"Input: {input_string}")
    print(f"Extracted paths: {extracted_paths}")
